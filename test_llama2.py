import replicate
from pathlib import Path
    

prompt_prefix = Path("../automarkup-training-toolkit/examples/configurestorage/prompt.txt").read_text()
xml = Path("../automarkup-training-toolkit/examples/configurestorage/configurestorage.rst.txt").read_text()
prompt = f"""
User:
    
{prompt_prefix}
    
XML:

{xml}
    
Assistant:

"""


prompt = """
User:

    Add tags to the following text to make it into a DITA Topic.

    Include this:

    <!DOCTYPE task PUBLIC "-//OASIS//DTD DITA Task//EN" "task.dtd">
    Keep the text as similar to the original as possible.

    Never remove content. Never add text other than tags.

    Here is an example of a task:

    <task id="bird-house-building">
    <title>Building a bird house</title>
    <shortdesc>Building a birdhouse is fun...</shortdesc>
    <taskbody>
    <prereq>To build a sound birdhouse, you will need a complete set of tools.</prereq>
    <context>Birdhouses provide safe locations for birds to build nests and raise their young. They also provide shelter during cold and rainy spells.</context>
    <steps> <step><cmd>Lay out the dimensions for the birdhouse elements.</cmd></step>
            <step><cmd>Cut the elements to size.</cmd></step>
            <step><cmd>Drill a 1 1/2" diameter hole for the bird entrance on the front.</cmd></step> <!--...--> 
    </steps>
    <result>You now have a beautiful new birdhouse!</result>
    <postreq>Now find a good place to mount it.</postreq>
    </taskbody>
    </task>

    Output ONLY the XML. No commentary.

    The text:

        Configuring hard storage devices
        ================================

        Most hard disks do not need any configuring. If they do, the
        instructions are relatively simple.

        First check the documentation that came with your storage device. If the
        device requires configuring, follow the steps below.

            #. If your system recognizes the device, it may be able to configure it
            without help. If so, do not try and stop it.
            #. Otherwise, your drive should come with software. Use this software to
            format and partition your drive.
            #. Once your drive is configured, restart the system. Just for fun. But
            be sure to remove any vendor software from your system before doing
            so.

    
Assistant:"""

prompt = """
User:

    Convert the following text into HTML:

               Configuring hard storage devices
        ================================

        Most hard disks do not need any configuring. If they do, the
        instructions are relatively simple.

        First check the documentation that came with your storage device. If the
        device requires configuring, follow the steps below.
 
Do not output ANY text other than the HTML. No commentary.

Assistant:

"""

print(prompt)

output = replicate.run(
    "replicate/llama70b-v2-chat:e951f18578850b652510200860fc4ea62b3b16fac280f83ff32282f87bbd2e48",
    input={"prompt": prompt},
    temperature = 0.75,
    max_tokens = 1000,
    top_p=1,
    repetition_penalty=1
)
# The replicate/llama70b-v2-chat model can stream output as it's running.
# The predict method returns an iterator, and you can iterate over that output.
for item in output:
    # https://replicate.com/replicate/llama70b-v2-chat/versions/e951f18578850b652510200860fc4ea62b3b16fac280f83ff32282f87bbd2e48/api#output-schema
    print(item)
