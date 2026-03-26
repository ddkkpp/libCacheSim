# Copilot 文件映射错误说明

在由 Windows 的 Copilot 环境远程控制 Linux/WSL 工作区时，可能会遇到可视化编辑工具（如 `apply_patch` / `replace_string_in_file`）报错 `File does not exist: <path>`，导致无法在 Copilot 界面上直观查看“保留”/“撤销”（Accept/Reject）按钮和修改 diff 的问题。

## 问题原因

1. **宿主与远端环境的路径解析差异**：
   当用户在 Windows 本地运行 VS Code，并通过 SSH 或 WSL 扩展附加到 Linux 远端时，Copilot 接收到的 Workspace 路径通常采用 Windows 风格或某种混合的 URI 形式（例如 `\\home\丁坤鹏\libcachesim_new`）。

2. **绝对路径验证失败**：
   可视化修补工具要求提供准确的绝对路径。由于存在非 ASCII 字符（如中文 `丁坤鹏`）的 URL 编码、以及反斜杠 `\` 转换为正斜杠 `/` 的中间层问题，如果提供带有主机/网络前缀的混淆路径（如 `\\home\丁坤鹏\...`），工具无法在远端 Linux 的真实文件系统中定位，被判定为“文件不存在”。

3. **修复方案（配置远端运行）**：
   要彻底解决该路径映射问题并恢复正常的可视化文件合并界面，需要配置 VS Code 使 Copilot 相关扩展强制在远端（Linux/WSL）工作区运行，而非由本地宿主机（Windows）代理解析。

   可在设置中添加如下配置，令其运行在远端主机：
   ```json
   "remote.extensionKind": {
       "github.copilot": [
           "workspace"
       ],
       "github.copilot-chat": [
           "workspace"
       ]
   }
   ```

   4. **代码匹配注意事项**：
   在明确使用远端挂载路径的前提下，调用 `apply_patch` / `replace_string_in_file` 时还要确保传入的 `oldString` 上下文（含换行及空白字符）需与远端文件中严格一致，方可成功替换。
