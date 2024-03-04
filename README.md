# Pipeline Usage

## 环境配置
采用的 SeeAct 使用的环境配置，不一定全部必要
- 进入Pipeline，bash setup.sh
- 在本地运行。记得修改.env里的 OpenAI API Key

## 同步 DEMO
python -m Pipeline.pipelines.interactive

注意：
- 修改 `gpt4v.py` 中的 `from templates.<template_name> import SYSTEM_PROMPT` 来使用不同的 template。目前在基础方案上，提供了一个支持 `while` 循环操作的template。

### 两套 Pipeline 区别
- simple_test.py 启动时会自动确认从什么网站开始
- AutoWebBench simple_test_v2.py的版本需要首先打开一个初始页面

### 输入输出格式
参考 template.py 中的示例，目前调整了整体 Prompt 格式

### (Optional) 保存数据
simple_test.py Pipeline 在运行时会自动保存 截图、绘制了 BBOX 框的截图和操作记录 JSON（尚未实现 HTML 的保存）。截图存放在Pipeline/temp里，JSON Trace 存放在 Pipeline/traces 里。


## 多并发数据构造（240223：尚未更新到最新框架）
使用 data_controller.py，调节 concurrency 参数控制并行协程数量

## 人工executor与加载历史功能
入口文件：`simple_test_manual_executor.py`  
执行指令：`python simple_test_manual_executor.py`  

注意：
1. 添加了 `.env` 的环境文件，负责存储gpt4的token，还有缓存的文件地址，请在Pipline目录下新建一个`.env`文件并粘贴一下内容  
```
GPT4V_TOKEN=""
TRACE_DIR="./traces"
```

2. 请安装 dotenv 依赖，指令： `pip install python-dotenv`
3. 修改了文件存储的格式，以每个任务为单位，将截图与对应的json文件一起存储，格式如下：  
```
* traces  
    * timestap # 每个任务通过timestap区分  
        * screenshot # 存储截图  
            * {turn}.png # 以turn的编号命名  
            * {turn}-bbox.png # 调用了executor api的结果，将bbox存储  
        * {timestap}.jsonl # 存储history           
```
4. 人工executor使用方法：在`simple_test_manual_executor.py`中设置`auto_executor = False`  
加载历史的注意事项：
* 人工执行会在每个步骤操作前停止，请执行完操作之后在控制台按回车继续
* 除了打开url、quote与exit的功能，其他功能都需要人工操作，包括点击、打字、翻页，下拉选择等。

5. 加载历史功能的使用方法
设置`reload_history`为`True`，并指定对应的恢复的轮次与jsonl的路径。示例：
```
reload_history = True
if reload_history:
    TURN_NUMBER = 3
    history_path = "./traces/1708670656/1708670656.jsonl"
```

加载历史的注意事项：
* 注意需要恢复的轮次！和jsonl中的index对应，保证jsonl中的所有prompt和response的内容为正确的。如果想修改某个轮次的agent指令，请修改对应index中的response。并删除这个轮次后面的所有内容！
* 查看这个轮次对应的截图内容是否正确，第i轮，应该查看第i-1轮的截图。
* 执行加载历史的程序之后，程序会第一次暂停，请按照控制台中输出的action，在新打开的浏览器页面中执行对应的操作，并回车。即可执行后续指令。

## Webarena 评测

首先需要从 dgx1 上转发端口到本地／开发机上：

```bash
ssh -fNL localhost:4399:localhost:4399 webarena@36.102.215.18 -p 2201
ssh -fNL localhost:7770:localhost:7770 webarena@36.102.215.18 -p 2201
ssh -fNL localhost:7780:localhost:7780 webarena@36.102.215.18 -p 2201
ssh -fNL localhost:8023:localhost:8023 webarena@36.102.215.18 -p 2201
ssh -fNL localhost:8888:localhost:8888 webarena@36.102.215.18 -p 2201
ssh -fNL localhost:9999:localhost:9999 webarena@36.102.215.18 -p 2201
```

进入 Pipeline 文件夹（仓库根目录下），添加环境文件 `.env`，并修改内容如下： 

```bash
GPT4V_TOKEN="<your-openapi-key>"
TRACE_DIR="./traces"
SCREENSHOT_DIR="./screenshots"

SHOPPING="http://localhost:7770"
SHOPPING_ADMIN="http://localhost:7780/admin"
REDDIT="http://localhost:9999"
GITLAB="http://localhost:8023"
MAP="http://ec2-3-131-244-37.us-east-2.compute.amazonaws.com:3000/"
WIKIPEDIA="http://localhost:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
HOMEPAGE="http://localhost:4399"
```

注意：需要更改 api-key 和端口为你实际使用的值。

接着需要配置环境：

```bash
conda create -n webarena python=3.10
conda activate webarena
pip install -r requirements.txt
playwright install
playwright install-deps
# install tmux for parallel test
apt-get update
apt install tmux -y
```

还需要使用 python 安装分词工具：

```python
# run this in python
import nltk
nltk.download('punkt')
```

然后运行 `bash webarena_test.sh` 生成测试数据和网页认证信息；

最后执行下面的指令即可开始评测：

```bash
cd ..
python -m Pipeline.pipelines.webarena_test --result_dir result
# eval
python Pipeline/webarena_tools/score.py result
```

| 参数        | 类型 | 用途                                               |
| ----------- | ---- | -------------------------------------------------- |
| --start_idx | int  | 指定测试开始的任务编号                             |
| --end_idx   | int  | 指定测试结束的任务编号                             |
| --sample    | int  | 仅测试编号为 sample 整数倍的任务 (全集测试请设为1) |
| --max_steps | int  | 每一个任务的最大交互回合数                         |
| --result_dir | str  | webarena 操作序列保存位置，主要用于分数计算   |
| --sites     | str  | 仅测试包含 sites 网页的任务，网页间用半型逗号分开* |

*网页可选项：shopping,shopping_admin,gitlab,reddit,wikipedia，默认全选。

多线程评测可使用下面的指令，注意更改 `parallel.sh` 内的 SAMPLE 和 run XX YY ZZ 来控制每进程的评测任务编号。

```bash
bash Pipeline/parallel.sh
```

