import json, re
from langchain import PromptTemplate, LLMChain
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
import pandas as pd

# Map month names to numbers
month_map = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "aug": 8,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


class TimelineBuilder:
    """
    A class to build a timeline from a text document
    """

    def __init__(
        self,
        timeline_title="Timeline",
        useful_info="",
        name_map=None,
        suppress_bracketted_dates=False,
        test_mode=False,
    ):
        """
        Initialize a TimelineAI object.

        Args:
            timeline_title (str): The title of the timeline.
            useful_info (str): Additional information to be passed to the prompt.
            name_map (dict): A dictionary mapping names to other names.
            suppress_bracketted_dates (bool): If True then bracketted dates are removed from the text.
        """

        self.timeline_title = timeline_title
        self.chunks = None
        self.timeline = None
        self.pages_filter = None
        self.pdf_name = None
        self.name_map = name_map
        self.useful_info = useful_info
        self.suppress_bracketted_dates = suppress_bracketted_dates
        self.test_mode = test_mode

    def load_data(self, file):
        """
        Loads data from a file.

        Args:
            file (str): The path to the file to be loaded.

        Raises:
            FileNotFoundError: If the specified file does not exist.

        """
        if file.endswith(".pdf"):
            loader = PyPDFLoader(file)
            self.chunks = loader.load_and_split()
        else:
            with open(file) as f:
                raw_doc = f.read()
            text_splitter = CharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            self.chunks = text_splitter.create_documents([raw_doc])

        self.pdf_name = file

    def preprocessing(self):
        """
        Preprocesses the texts by removing unwanted characters.

        Returns:
            None
        """
        # Remove bracketted dates
        if self.suppress_bracketted_dates:
            for c in self.chunks:
                c.page_content = re.sub(r"\(\d{4\s*-\s*\d{4}\)", "", c.page_content)

    def pass_to_llm(self):
        """
        Passes the texts to the language model to extract events.

        Returns:
            None
        """
        self.responses = []
        if self.test_mode:
            self.chunks = self.chunks[:4]
        for text in self.chunks:
            response = {
                "llm_response": self.prompt_llm(text.page_content),
                "page": text.metadata["page"] + 1,
                "source": text.page_content,
            }
            self.responses.append(response)

    def prompt_llm(self, text):
        """
        Extracts a timeline with dates from the given text and returns it as a JSON array of event objects.

        Args:
            text (str): The input text from which to extract the timeline.

        Returns:
            str: The extracted timeline as a JSON array of event objects.
        """

        template = """
        Extract a timeline with dates from the text given below. The timeline should be stored in json as an array
        of event objects where each event has the attributes "year", "month", "day_of_month" and "event". If the month and day
        of month are unknown then they should be left blank. {useful_info}

        Here is the text: {page}.
        """

        prompt = PromptTemplate(
            template=template, input_variables=["page", "useful_info"]
        )
        llm_chain = LLMChain(
            prompt=prompt, llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        )
        response = llm_chain.run({"page": text, "useful_info": self.useful_info})

        response = response.replace("```json", "").replace("```", "").strip()

        return response

    def check_response_format(self):
        """
        Check the format of each response in the list and update the response dictionary accordingly.

        This method iterates over each response in the list and attempts to parse it as a JSON object.
        If the parsing is successful, the response is marked as having a valid format and the parsed JSON object is stored.
        If the parsing fails, the response is marked as having an invalid format and the parsed JSON object is set to None.

        Returns:
            None
        """

        for r in self.responses:
            try:
                # Read the response as a JSON object
                r["response_as_json"] = json.loads(r["llm_response"])
                r["valid_format"] = True
            except ValueError:
                r["response_as_json"] = None
                r["valid_format"] = False

    def transform_events(self):
        """
        Transforms the events by combining them from multiple responses and adding additional information.

        This method iterates over the responses and combines the events from each response into a single list.
        It also adds the source and page information to each event. Finally, it transforms each event using the
        `transform_event` method and adds it to the timeline.

        Returns:
            None
        """
        events = []
        for r in self.responses:
            if r["valid_format"]:
                for e in r["response_as_json"]:
                    e["source"] = r["source"]
                    e["page"] = r["page"]
                    events.append(e)
        self.timeline = []
        for e in events:
            trans_event = self.transform_event(e)
            self.timeline.append(self.transform_event(e))

    def transform_event(self, e):
        """
        Transforms the event dictionary by normalizing the values of the 'month', 'day_of_month', and 'year' keys.

        Args:
            e (dict): The event dictionary to be transformed.

        Returns:
            dict: The transformed event dictionary.
        """

        if "month" not in e:
            e["month"] = ""

        if "day_of_month" not in e:
            e["day_of_month"] = ""

        if isinstance(e["month"], int):
            if e["month"] < 0 or e["month"] > 12:
                e["month"] = 0
        elif isinstance(e["month"], str):
            if e["month"].lower() in month_map:
                e["month"] = month_map[e["month"].lower()]
            elif e["month"] in [str(i) for i in range(1, 13)]:
                e["month"] = int(e["month"])
            else:
                e["month"] = 0
        else:
            e["month"] = 0

        if isinstance(e["day_of_month"], int):
            pass
        elif isinstance(e["day_of_month"], str) and e["day_of_month"].isdigit():
            e["day_of_month"] = int(e["day_of_month"])
        else:
            e["day_of_month"] = 0

        if isinstance(e["year"], int):
            pass
        elif isinstance(e["year"], str) and e["year"].isdigit():
            e["year"] = int(e["year"])
        else:
            e["year"] = None

        return e

    def deduplicate_timeline(self):
        """
        Removes duplicate events from the timeline.

        This method removes duplicate events from the timeline by checking for duplicates based on the "event" and "year" columns.
        Only events with non-null years are considered for deduplication.

        Returns:
            None
        """
        df = pd.DataFrame(self.timeline)
        df = df[df["year"] != None]
        df = df.drop_duplicates(subset=["event", "year"])
        self.timeline = df.to_dict(orient="records")

    def check_json_format(self, events):
        """
        Check if the given events object is in the correct JSON format.

        Args:
            events (list): A list of events.

        Returns:
            bool: True if the events object is in the correct format, False otherwise.
        """

        # Check that the events object is a list
        if not isinstance(events, list):
            print("Events is not a list")
            return False

        # Check that each event is a dictionary
        for event in events:
            if not isinstance(event, dict):
                print("Event is not a dictionary")
                return False

        for e in events:
            # Check that each event has the required attributes
            field_names = ["year", "month", "day_of_month", "event"]
            for f in field_names:
                if f not in e:
                    print("Event does not have required attribute")
                    return False

        return True

    def create_timeline_diagram(self, file_out, start_year, end_year, width=3000):
        """
        Creates a timeline diagram and saves it as an HTML file.

        Args:
            file_out (str): The output file name (without the extension).
            start_year (int): The starting year of the timeline.
            end_year (int): The ending year of the timeline.
            width (int, optional): The width of the diagram in pixels. Defaults to 3000.

        Returns:
            None
        """
        head = (
            """
        <link rel="stylesheet" href="https://unpkg.com/d3-milestones/build/d3-milestones.css">
        <style>
            div {
                pointer-events: none;
            }

            a {
                pointer-events: auto;
                text-decoration: none;
                color: inherit;
            }
            </style>
        <script src="https://unpkg.com/d3-milestones/build/d3-milestones.min.js"></script>
        <div id="tooltip"
        style="position: absolute; opacity: 0; padding: 10px; background-color: whitesmoke; border: 1px solid black; border-radius: 5px; width:300px; font-size: 8pt;">
        </div>
        <div>
            <h2>"""
            + self.timeline_title
            + "</h2></div>"
        )

        script_tail = """
        ]);
        """

        script = """
        <script>milestones('#test')
        .mapping({
          'timestamp': 'year',
          'text': 'title'
        })
        .parseTime('%Y/%-m/%-d')
        .aggregateBy('month')
        .orientation('horizontal')
        .useLabels(true)
        .optimize(true)
        .render([
        """
        js_string = [
            {"year": "{}/1/1".format(start_year), "title": "Start of timeline"}
        ]
        for e in self.timeline:
            if e["year"] > start_year and e["year"] < end_year:
                js_string.append(
                    {
                        "year": "{}/{}/{}".format(
                            e["year"],
                            1 if e["month"] == 0 or e["month"] == "" else e["month"],
                            1 if e["day_of_month"] == 0 else e["day_of_month"],
                        ),
                        "title": (
                            e["event"] + " (year level)"
                            if e["month"] == 0 or e["month"] == ""
                            else e["event"]
                        ),
                        "page": e["page"],
                        "url": self.pdf_name + "#page=" + str(e["page"]),
                    }
                )
        js_string.append(
            {"year": "{}/1/1".format(end_year), "title": "End of timeline"}
        )
        js_string = json.dumps(js_string)
        script = script + js_string + script_tail
        script = script + "</script>"

        html_file = "{}.html".format(file_out)
        write_file = open(html_file, "w")
        write_file.write(
            head
            + "\n".join(
                ["""<div id="{}" style="width:{}px;"></div>""".format("test", width)]
            )
            + script
        )
        write_file.close()


def check_birth_string(input_str):

    if input_str[:5].lower() == "birth":
        input_str = "The birth" + input_str[5:]

    # Remove anything withing curved brackets
    input_str = re.sub(r"\([^()]*\)", "", input_str)

    # Define the pattern to match "X is born" or "X born"
    pattern = re.compile(r"^(?P<name>\w+)\s+(?:is\s+)?born$", re.IGNORECASE)

    # Try to match the pattern
    match = pattern.match(input_str.strip())

    if match:
        name = match.group("name")
        return f"The birth of {name}"
    else:
        return input_str


"""
When a person's name is followed by two dates in brackets then 
        the first date is the birth date and the second date is the death date. You should include both the birth and the death
        in the timeline. For example, "Albert Einstein (1879-1955)" should be included as two events, one for the birth and one
        for the death. 
"""
