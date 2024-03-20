'''

你的任务是根据一行可执行代码，推测当前正在执行的任务计划是什么。这段可执行代码是为了操作一台安卓手机而设计的，包括了点击（tap），滑动（swipe），打字（type）等操作。代码中的find_element_by_instruction函数是为了在屏幕上找到这一元素。可执行代码的定义如下：

def do(action, argument=None, element=None, **kwargs):
    """
    A single operation on an Android mobile device.

    Args:
        :param action: one of the actions from ["Tap", "Type", "Swipe", "Long Press","Press Home", "Press Back", "Press Enter", "Wait"].
        :param argument: optional. For "Type" actions, indicating the content to type in. After "Type" actions, "Press Enter" action is automatically executed.
                                   For "Swipe" actions, indicating the direction to swipe. Should be one of ["up", "down", "left", "right"]. An additional optional argument "dist" can be used, shoule be one of ["long", "medium", "short"].
        :param element: optional. For "Tap" and "Long Press". Should be acquired from functions similar to find_element_by_instruction* but designed for mobile UI elements.
                                  For "Swipe" actions, You can provide the element to swipe on by find_element_by_instruction*, or not provide default from screen center.

    Returns:
        None. The device state or the foreground application state will be updated after executing the action.
    """

def find_element_by_instruction(instruction):
	"""A function that finds the elemention given natural language instructions.
	You must describe the location of the element on the page, such as "bottom left", "top right", "middle center".
	Remember to include both horizontal and vertical description.
	Target element must exist on current screenshot.

	Args:
		:param instruction: a string of instruction that describes the action and element to operate. Must include locative description of the element.

	Returns:
		element.
	"""

你应当充分利用可执行代码中给出的信息，并且给出对应的自然语言任务计划。你不可以添加额外的信息，也不可以修改可执行代码的定义。

###代码：
do(action="Tap", argument=None, element=find_element_by_instruction(instruction="The Clock app is located on the bottom left of the screen."))
###返回值：
Open the Clock app.
###代码：
do(action="Tap", argument=None, element=find_element_by_instruction(instruction="The Alarm tab located on the bottom left of the screen."))
###返回值：
I should tap on the Alarm tab
###代码：
do(action="Tap", element=find_element_by_instruction(instruction="The search bar at the top of the screen."))
###返回值：
'''