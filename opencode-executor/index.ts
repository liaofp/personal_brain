import { BasePlugin, PluginContext, ToolExecuteResult } from '@openclaw/plugin-sdk';
import { execSync, spawn } from 'child_process';

export default class OpenCodeOrchestratorPlugin extends BasePlugin {
  // 🔒 控制面单例内存锁
  private isEvolving: boolean = false;

  async onInitialize(context: PluginContext): Promise<void> {
    context.logger.info('🚀 OpenClaw 超级进化调度插件成功注入，已全权剥离硬编码参数。');
  }

  async onTrigger(args: { target_file: string; instruction: string }, context: PluginContext): Promise<ToolExecuteResult> {
    const { target_file, instruction } = args;

    if (this.isEvolving) {
      context.emit('stream:start', { message: '⚠️ 生产安全拦截：当前已有另一个自动化编码任务正在独占修改代码库，请稍候。' });
      return { success: false, error: 'Parallel evolution locked.' };
    }

    this.isEvolving = true;
    context.emit('stream:start', { message: `🧠 [OpenClaw 控制面接收指令] 目标文件: ${target_file}\n` });

    // 💡 从环境变量中动态提取参数，无缝适配 Windows/Linux 物理边界
    const hostProjectPath = process.env.HOST_PROJECT_PATH;
    const dockerSockPath = process.env.DOCKER_SOCK_PATH || '/var/run/docker.sock';
    const productionContainer = process.env.PRODUCTION_CONTAINER_NAME || 'personal_brain_runtime';
    const openCodeImage = process.env.OPENCODE_IMAGE;

    if (!hostProjectPath || !openCodeImage) {
      this.isEvolving = false;
      return { success: false, error: '配置项缺失：请检查 .env 中的 HOST_PROJECT_PATH 和 OPENCODE_IMAGE' };
    }

    try {
      // 1. 彻底解决数据库死锁与写冲突：主动下线业务微服务容器
      context.emit('stream:data', { chunk: `🔄 [控制面安全调度] 正在优雅暂停运行期微服务容器 [${productionContainer}]，彻底释放 SQLite 文件锁...\n` });
      try {
        execSync(`docker stop ${productionContainer}`);
        context.emit('stream:data', { chunk: `✅ 业务容器已安全离线，物理文件锁已完全解除。\n` });
      } catch (err) {
        context.logger.warn('业务容器当前未拉起，略过停止动作。');
      }

      // 2. 原生管理 OpenCode 容器的生命周期
      context.emit('stream:data', { chunk: `🤖 [控制面安全调度] 正在拉起全能型 OpenCode 专家容器，进入工作区执行 [取-规-改-测-交] 全闭环...\n\n` });
      
      const dockerArgs = [
        'run', '--rm',
        '-v', `${hostProjectPath}:/workspace`,
        // 💡 关键所在：动态挂载当前系统的 Docker 套接字，允许 OpenCode 内部调用宿主机引擎
        '-v', `${dockerSockPath}:/var/run/docker.sock`, 
        '-e', `DEEPSEEK_API_KEY=${process.env.DEEPSEEK_API_KEY}`,
        '-e', `DEEPSEEK_BASE_URL=${process.env.DEEPSEEK_BASE_URL}`,
        '-e', `DEEPSEEK_MODEL=${process.env.DEEPSEEK_MODEL}`,
        '-e', `GITHUB_TOKEN=${process.env.GITHUB_TOKEN}`,
        '-e', `GITHUB_REPO_URL=${process.env.GITHUB_REPO_URL}`,
        '-e', `GIT_AUTHOR_NAME=${process.env.GIT_AUTHOR_NAME}`,
        '-e', `GIT_AUTHOR_EMAIL=${process.env.GIT_AUTHOR_EMAIL}`,
        '-w', '/workspace',
        openCodeImage,
        'opencode-agent', '--target', target_file, '--instruction', instruction
      ];

      // 3. 动态唤醒并实时监控 OpenCode 容器进程，实现日志穿透
      await new Promise<void>((resolve, reject) => {
        const opencodeProcess = spawn('docker', dockerArgs);

        opencodeProcess.stdout.on('data', (data) => {
          context.emit('stream:data', { chunk: data.toString() });
        });

        opencodeProcess.stderr.on('data', (data) => {
          context.emit('stream:data', { chunk: data.toString() });
        });

        opencodeProcess.on('close', (code) => {
          if (code === 0) {
            resolve();
          } else {
            reject(new Error(`OpenCode 专家自修复耗尽，未能通过回归测试。退出码: ${code}`));
          }
        });
      });

      context.emit('stream:data', { chunk: '\n🎉 [控制面成功] OpenCode 编码、回归测试、Git自动提交全部顺利交卷！\n' });

    } catch (error: any) {
      context.emit('stream:data', { chunk: `\n❌ \x1b[31m[控制面安全防御拦截] 演进失败：${error.message}\x1b[0m\n` });
      this.isEvolving = false;
      // 发生异常时，依然无条件恢复常驻业务生产环境
      execSync(`docker start ${productionContainer}`);
      return { success: false, error: error.message };
    }

    // 4. 优雅自愈重启：重新拉起业务容器，Python 在冷启动中自动加载全新代码对象
    context.emit('stream:data', { chunk: `🔌 [控制面安全自愈] 正在重新拉起微服务常驻运行容器，无缝重载最新内存路由...\n` });
    execSync(`docker start ${productionContainer}`);
    context.emit('stream:data', { chunk: `🚀 业务微服务已重新上线，进化版应用成功加载！\n` });
    
    this.isEvolving = false;
    context.emit('stream:end', { status: 'completed' });

    return { success: true, output: 'OpenClaw 原生管控自进化链路完美闭环。' };
  }

  async onDestroy(context: PluginContext): Promise<void> {}
}