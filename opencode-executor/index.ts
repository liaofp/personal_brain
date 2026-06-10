import { BasePlugin, PluginContext, ToolExecuteResult } from '@openclaw/plugin-sdk';
import { execSync, spawn } from 'child_process';
import path from 'path';

// ── 超时常量（毫秒）──────────────────────────────────────────
const TIMEOUT_DOCKER_STOP_MS  = 30_000; 
const TIMEOUT_DOCKER_START_MS = 30_000; 
const DOCKER_STOP_GRACE_SEC   = 20;

// ── 工具函数：带超时的 docker 命令执行 ─────────────────────────
/**
 * 安全执行 docker CLI 命令，强制设置超时上限。
 *
 * @param args      docker 子命令及参数数组，例如 ['stop', '--time', '20', 'my_container']
 * @param timeoutMs 超时毫秒数，超时后抛出 Error
 * @param label     日志标签，用于错误信息定位
 */
function safeDockerExec(args: string[], timeoutMs: number, label: string): void {
  const cmd = `docker ${args.join(' ')}`;
  try {
    execSync(cmd, {
      timeout: timeoutMs,
      // 将 stdout/stderr 吞掉，避免大量日志阻塞 execSync 的内部 pipe 缓冲区
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (err: any) {
    // Node.js 在 execSync 超时时，err.signal === 'SIGTERM'，err.killed === true
    if (err.killed || err.signal === 'SIGTERM') {
      throw new Error(
        `[${label}] docker 命令超时（>${timeoutMs}ms）被强制终止: ${cmd}`
      );
    }
    // 其他错误（容器不存在、守护进程未启动等）原样抛出，附加上下文
    const errorDetail = err.stderr ? err.stderr.toString().trim() : err.message;
    throw new Error(`[${label}] docker 命令执行失败: ${cmd}\n底层原因: ${errorDetail}`);    
  }
}

// ── 插件主体 ─────────────────────────────────────────────────
export default class OpenCodeOrchestratorPlugin extends BasePlugin {
  /** 控制面单例内存锁：防止并发进化任务同时修改代码库 */
  private isEvolving: boolean = false;

  async onInitialize(context: PluginContext): Promise<void> {
    context.logger.info('🚀 OpenClaw 超级进化调度插件成功注入，已全权剥离硬编码参数。');
  }

  async onTrigger(
    args: { target_file: string; instruction: string },
    context: PluginContext
  ): Promise<ToolExecuteResult> {
    const { target_file, instruction } = args;

    // ── 并发保护 ──────────────────────────────────────────────
    if (this.isEvolving) {
      context.emit('stream:start', {
        message: '⚠️ 生产安全拦截：当前已有另一个自动化编码任务正在独占修改代码库，请稍候。',
      });
      return { success: false, error: 'Parallel evolution locked.' };
    }

    // ✅ 修复：将 isEvolving 的重置移入 finally，无论何种退出路径都能保证解锁
    this.isEvolving = true;

    context.emit('stream:start', {
      message: `🧠 [OpenClaw 控制面接收指令] 目标文件: ${target_file}\n`,
    });

    // ── 环境变量读取 ──────────────────────────────────────────
    const hostProjectPath    = process.env.HOST_PROJECT_PATH; 
    const dockerSockPath     = process.env.DOCKER_SOCK_PATH || '/var/run/docker.sock';
    const productionContainer = process.env.PRODUCTION_CONTAINER_NAME || 'personal_brain_runtime'; 
    const openCodeImage      = process.env.OPENCODE_IMAGE; 

    if (!hostProjectPath || !openCodeImage) {
      this.isEvolving = false; 
      return {
        success: false,
        error: '配置项缺失：请检查 .env 中的 HOST_PROJECT_PATH 和 OPENCODE_IMAGE', 
      };
    }

    const projectName = path.basename(hostProjectPath.trim()); 

    try {
      // ── Step 1: 优雅停止业务容器，释放 SQLite 文件锁 ─────────
      context.emit('stream:data', {
        chunk: `🔄 [控制面安全调度] 正在优雅暂停运行期微服务容器 [${productionContainer}]，彻底释放 SQLite 文件锁...\n`,
      });

      try {
        // ✅ 修复：
        //   原代码：execSync(`docker stop ${productionContainer}`)  — 无超时，可能永久阻塞
        //   修复后：
        //     a. 通过 --time 参数给容器 DOCKER_STOP_GRACE_SEC 秒做优雅退出（SIGTERM → SIGKILL）
        //     b. safeDockerExec 的 timeout 选项作为外层硬性上限兜底，防止 docker CLI 本身卡死
        //   注意 DOCKER_STOP_GRACE_SEC < TIMEOUT_DOCKER_STOP_MS/1000，两个超时互不重叠
        safeDockerExec(
          ['stop', '--time', String(DOCKER_STOP_GRACE_SEC), productionContainer],
          TIMEOUT_DOCKER_STOP_MS,
          'docker-stop'
        );
        context.emit('stream:data', {
          chunk: `✅ 业务容器已安全离线，物理文件锁已完全解除。\n`,
        });
      } catch (stopErr: any) {
        // 容器本身不存在（未启动）是正常情况，记录 warn 后继续
        context.logger.warn(`业务容器停止时出现非致命异常，略过: ${stopErr.message}`);
      }

      // ── Step 2: 拉起 OpenCode 专家容器执行代码进化 ────────────
      context.emit('stream:data', { chunk: `🤖 [控制面安全调度] 正在拉起全能型 OpenCode 专家容器，进入工作区 [${projectName}] 执行进化...\n\n`, });

      const dockerArgs: string[] = [
        'run', '--rm',
        '-v', `${hostProjectPath}:/workspace/${projectName}`,
        '-v', `${dockerSockPath}:/var/run/docker.sock`, 
        '-v', `${hostProjectPath}/opencode_config.json:/root/.config/opencode/config.json:ro`,
        '-e', `DEEPSEEK_API_KEY=${process.env.DEEPSEEK_API_KEY}`, 
        '-e', `DEEPSEEK_BASE_URL=${process.env.DEEPSEEK_BASE_URL}`,
        '-e', `DEEPSEEK_MODEL=${process.env.DEEPSEEK_MODEL}`,
        '-e', `GITHUB_TOKEN=${process.env.GITHUB_TOKEN}`,
        '-e', `GITHUB_REPO_URL=${process.env.GITHUB_REPO_URL || ''}`,
        '-e', `GIT_AUTHOR_NAME=${process.env.GIT_AUTHOR_NAME || 'OpenCode-Agent'}`,
        '-e', `GIT_AUTHOR_EMAIL=${process.env.GIT_AUTHOR_EMAIL || 'agent@openclaw.local'}`,
        '-e', `PROJECT_NAME=${projectName}`,
        '-e', `REPO_NAME=${projectName}`,
        '-w', `/workspace/${projectName}`,
        openCodeImage,
        'opencode-agent', '--target', target_file, '--instruction', instruction,
      ];

      // ── Step 3: 实时监控 OpenCode 容器进程，日志穿透流式输出 ──
      // spawn 本身是异步的，不需要额外超时保护（OpenCode 自身应有任务超时机制）
      await new Promise<void>((resolve, reject) => {
        const opencodeProcess = spawn('docker', dockerArgs);

        const timeoutTimer = setTimeout(() => {
          opencodeProcess.kill('SIGKILL');
          reject(new Error(`OpenCode 演进任务超过生产安全时限（${TIMEOUT_OPENCODE_TASK_MS / 60000}分钟），已被强制终止。`));
        }, TIMEOUT_OPENCODE_TASK_MS);

        opencodeProcess.stdout.on('data', (data: Buffer) => {
          context.emit('stream:data', { chunk: data.toString() });
        });

        opencodeProcess.stderr.on('data', (data: Buffer) => {
          context.emit('stream:data', { chunk: data.toString() });
        });

        opencodeProcess.on('close', (code: number | null) => {
          clearTimeout(timeoutTimer);
          if (code === 0) {
            resolve();
          } else {
            reject(
              new Error(`OpenCode 专家自修复耗尽，未能通过回归测试。退出码: ${code}`)
            );
          }
        });

        opencodeProcess.on('error', (err: Error) => {
          clearTimeout(timeoutTimer);
          reject(new Error(`无法启动 OpenCode 容器进程: ${err.message}`));
        });
      });

      context.emit('stream:data', {
        chunk: '\n🎉 [控制面成功] OpenCode 编码、回归测试、Git自动提交全部顺利交卷！\n',
      });

    } catch (error: any) {
      // ── 异常路径：尝试恢复业务容器，记录日志，返回失败 ────────
      context.emit('stream:data', {
        chunk: `\n❌ \x1b[31m[控制面安全防御拦截] 演进失败：${error.message}\x1b[0m\n`,
      });

      try {
        context.emit('stream:data', {
          chunk: `🔌 [容器恢复] 正在尝试恢复业务容器 [${productionContainer}]...\n`,
        });
        safeDockerExec(['start', productionContainer], TIMEOUT_DOCKER_START_MS, 'docker-start-recovery');
        context.emit('stream:data', {
          chunk: `✅ 业务容器已恢复上线。\n`,
        });
      } catch (startErr: any) {
        // 恢复失败是严重问题，记录 error 级别日志，供运维排查
        context.logger.error(
          `⚠️ 严重：演进失败后尝试恢复容器也未成功，请立即人工介入！原因: ${startErr.message}`
        );
      }

      // isEvolving 由 finally 统一重置，此处不需要手动 false
      return { success: false, error: error.message };

    } finally {
      try {
        context.emit('stream:data', { chunk: `🧹 [系统自净] 正在静默清理 OpenCode 演进产生的临时卷与虚悬镜像...\n` });
        safeDockerExec(['system', 'prune', '-f', '--volumes'], TIMEOUT_DOCKER_PRUNE_MS, 'docker-prune');
        context.emit('stream:data', { chunk: `✨ 宿主机 Docker 环境清理完毕。\n` });
      } catch (pruneErr: any) {
        // prune 失败不应阻断代码主链路，记录一条 warn 日志即可
        context.logger.warn(`[系统自净] 静默清理失败（非致命）: ${pruneErr.message}`);
      }
      this.isEvolving = false;
    }

    // ── Step 4: 成功路径：重启业务容器，加载进化后的代码 ────────
    context.emit('stream:data', {
      chunk: `🔌 [控制面安全自愈] 正在重新拉起微服务常驻运行容器，无缝重载最新内存路由...\n`,
    });

    try {
      safeDockerExec(['start', productionContainer], TIMEOUT_DOCKER_START_MS, 'docker-start-success');
      context.emit('stream:data', {
        chunk: `🚀 业务微服务已重新上线，进化版应用成功加载！\n`,
      });
    } catch (startErr: any) {
      context.logger.error(`重启业务容器失败，请手动执行 docker start ${productionContainer}: ${startErr.message}`);
      context.emit('stream:data', {
        chunk: `⚠️ 容器重启失败，代码已更新但服务未自动上线，请手动执行: docker start ${productionContainer}\n`,
      });
    }

    context.emit('stream:end', { status: 'completed' });

    return { success: true, output: 'OpenClaw 原生管控自进化链路完美闭环。' };
  }

  async onDestroy(context: PluginContext): Promise<void> {}
}