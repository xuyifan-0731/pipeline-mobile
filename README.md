# Pipeline Usage

## Mobile Pipeline Usage

1. 参照appagent安装ADB和android studio，并且在本机启动android虚拟机，或按照ADB并且连接真机。确保命令行执行adb device有结果。可参考一下步骤
   1. On your PC, download and install [Android Debug Bridge](https://developer.android.com/tools/adb) (adb) which is a
      command-line tool that lets you communicate with your Android device from the PC.
   2. Get an Android device and enable the USB debugging that can be found in Developer Options in Settings.

   3. Connect your device to your PC using a USB cable.

   4. (**if without Android device**) If you do not have an Android device. We recommend you download
      [Android Studio](https://developer.android.com/studio/run/emulator) and use the emulator that comes with it.
      The emulator can be found in the device manager of Android Studio. You can install apps on an emulator by
      downloading APK files from the internet and dragging them to the emulator.
      AppAgent can detect the emulated device and operate apps on it just like operating a real device.
   5. 为了支持中文输入，需要在手机安装adbkeyboard.apk，可以在[这里](https://github.com/senzhk/ADBKeyBoard/tree/master/)下载，安装后在adb指令执行:
       ```
        adb shell ime enable com.android.adbkeyboard/.AdbIME
        adb shell ime set com.android.adbkeyboard/.AdbIME
        ```

2. 根据config_files/example.yaml中的例子创建一个yaml文件，在里面填写:

   ```
   GPT4V_TOKEN: your token
   LOG_DIR: ./logs
   ```

3. pip install -r requirement.txt

4. python mobile_test.py 目前需要在mobile_test.py 中修改instruction,并且添加第二步中的yaml文件路径

## Auto Evaluation
自动评测（完整评测）需要对yaml文件内容进行一定修改，在里面增加以下内容：
   ```
GPT4V_TOKEN: 
LOG_DIR: ./logs
AVD_BASE: /Users/YourUserName/.android/avd
AVD_NAME: test_device
ANDROID_SDK_PATH: /Users/YourUserName/Library/Android/sdk
EVA_DATASET: ./evaluation_dataset/query.xlsx
PROMPT: android_template
   ```
其中，AVD_BASE为AVD的存放路径，AVD_NAME为AVD的名字。应当存在一个AVD_BASE/AVD_NAME.ini 和 AVD_BASE/AVD_NAME.avd文件。
ANDROID_SDK_PATH为Android SDK的路径。
EVA_DATASET为评测数据集的路径，目前设定为excel，其中有id，app和query三列，id要求唯一。默认的执行语句为"打开{app}, {query}"，可以在evaluation_emulator.py中修改。
同时，在evaluation.py的main函数传入参数中指定正确的yaml文件路径。

完成以上配置后，运行evaluation_emulator.py即可，结果保存在evaluation_logs/时间戳文件夹中。

如果想要使用预设的prompt，在yaml文件中添加PROMPT: android_template，然后在templates/one_shot_prompt中添加相应名字的txt文件。txt的名字与query.xlsx中的app名字一致。

如果要使用真机评测，运行evaluation_real.py即可，结果保存在evaluation_logs/时间戳文件夹中。注意，真机评测中，需要在evaluation_real的get_package_name函数中，添加app和对应的package name，否则无法正常执行。

## 在 MacOS 上运行的几个注意事项

1. Mac 上的 `adb` 可能需要通过加载环境变量的方式运行，但是默认的方案中不会主动加载环境变量，因此需要调整 `and_controller.py` 中的 `execute_adb` 函数实现：
```python
env = os.environ.copy()
env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/platform-tools:" + env["PATH"]
env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/tools:" + env["PATH"]
result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                      executable='/bin/zsh', env=env)
```
2. 如果遇到模拟器没有网络的情况，考虑在命令行启动时加入 `-no-snapshot-load` 参数（等同于重装系统）来恢复网络配置
3. Emulator 通过命令行启动时，不会主动采用宿主机的 system proxy（如下方式启动）
```bash
emulator -avd Pixel_3a_API_34_extension_level_7_arm64-v8a -netdelay none -netspeed full -no-snapshot-load 
```
如果需要使用宿主机的 system proxy，需要将 emulator 的网络连接设置为 AndroidWifi，然后设置该 Wifi 的 Proxy 为 `10.0.2.2:<proxy_port>`，其中 `10.0.2.2` 为 emulator 默认分配给宿主机的 IP 地址。


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

SHOPPING="http://localhost:7773"
SHOPPING_ADMIN="http://localhost:7783/admin"
REDDIT="http://localhost:9993"
GITLAB="http://localhost:8026"
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

然后执行如下指令生成测试数据和网页认证信息；

```bash
cd ..
python -m Pipeline.webarena_tools.generate_test_data
mkdir -p ./.auth
python -m Pipeline.webarena_tools.auto_login
```

最后执行下面的指令即可开始评测：

```bash
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

