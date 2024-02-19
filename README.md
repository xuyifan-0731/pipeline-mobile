# Pipeline Usage

## 环境配置
采用的 SeeAct 使用的环境配置，不一定全部必要
- 进入Pipeline，bash setup.sh
- 启动命令：返回到上级目录，python -m Pipeline.simple_test
- 在本地运行。记得修改gpt4v.py里的 OpenAI API Key

## 同步 DEMO（供测试）
simple_test.py & simple_test_v2.py

### 两套 Pipeline 区别
- simple_test.py 启动时会自动确认从什么网站开始
- AutoWebBench simple_test_v2.py的版本需要首先打开一个初始页面

### 输入输出格式
参考 template.py 中的示例，目前调整了整体 Prompt 格式

### (Optional) 保存数据
simple_test.py Pipeline 在运行时会自动保存 截图、绘制了 BBOX 框的截图和操作记录 JSON（尚未实现 HTML 的保存）。截图存放在Pipeline/temp里，JSON Trace 存放在 Pipeline/traces 里。


## 多并发数据构造
使用 data_controller.py，调节 concurrency 参数控制并行协程数量
