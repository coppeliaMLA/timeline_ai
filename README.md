# timeline ai

![](/assets/byron_screenshot.png)

## About the project

This python package uses a large language model (currently OpenAI's *gpt-3.5-turbo*) to extract and then visualise (using the brilliant [d3-milestones package](https://github.com/walterra/d3-milestones)) historical time lines from pdf documents. 

Here are some example outputs:

- [The life and works of Lord Byron](https://www.coppelia.io/timeline_ai/byron.html) extracted from the [National Dictionary of Biography](https://www.coppelia.io/timeline_ai/byron_bio.pdf#page=1).
- [A history of the world since the American War of Independence](https://www.coppelia.io/timeline_ai/short_history.html) extracted from the last thirteen chapters of [H G Wells A Short History of the World](https://www.coppelia.io/timeline_ai/shotw_chap_64_onwards.pdf).

As with all uses of LLMs there is the possibility of [hallucinations](https://en.wikipedia.org/wiki/Hallucination_(artificial_intelligence)) and so it is crucial that the information is verifiable. You can do this by clicking on each event on the timeline. You will then be taken to the page of the pdf from which the event was extracted.

## Installation

Install using pip either directly from github...

```
pip install timeline_ai@git+https://github.com/coppeliaMLA/timeline_ai
```

Or if you have cloned the repository simply run `pip install .` from the repository root.

## Obtaining an Openai API Key

You will need an to run the package. Instructions for obtaining the key are [here](https://platform.openai.com/docs/quickstart?context=python). Note the service is not free! Once you have the key you will need to add it to your environment variables. See [this notebook](examples/examples.ipynb) for an example of how to do this in python.

## Usage

A single line of code will generate the timeline.

```
import timeline_ai as ta

ta.build_timeline(pdf_file="byron_bio.pdf",
    output_file = "byron.html",
    timeline_title = "Byron's life and works",
    start_year = 1780,
    end_year = 1830)
```

The arguments to the function are as follows:

- `pdf_file` (str): The path to the PDF file containing the timeline data.
- `output_file` (str): The path to save the generated timeline diagram.
- `timeline_title` (str): The title of the timeline.
- `start_year` (int): The starting year of the timeline.
- `end_year` (int): The ending year of the timeline.
- `useful_info` (str, optional): Additional information to pass to the LLM prompt.
       
You can find a jupyter notebook for generating the above examples [here](examples/examples.ipynb)
