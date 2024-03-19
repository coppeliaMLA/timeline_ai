import json, re
from langchain import PromptTemplate, LLMChain
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader


class TimelineBuilder:
    """
    A class to build a timeline from a text document
    """

    def __init__(self):
        self.texts = None
        self.timeline = None
        self.pages_filter = None
        self.pdf_name = None

    def load_data(self, file, pages_filter=None):
        """
        Load data from a file.

        Args:
            file (str): The path to the file to load.
            pages_filter (tuple, optional): A tuple specifying the range of pages to load. Defaults to None.

        Returns:
            None
        """

        if file.endswith(".pdf"):
            loader = PyPDFLoader(file)
            pages = loader.load_and_split()
            if pages_filter is not None:
                self.texts = pages[pages_filter[0] : pages_filter[1]]
            else:
                self.texts = pages
        else:
            with open(file) as f:
                raw_doc = f.read()
            text_splitter = CharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            self.texts = text_splitter.create_documents([raw_doc])

        self.pages_filter = pages_filter
        self.pdf_name = file

    def run_across_chunks(self):
        """
        Runs the timeline generation process across chunks of texts.

        This method iterates over the texts in the `self.texts` list and extracts events from each text's page content.
        Each event is then assigned the source page content. The extracted events are appended to the `timeline` list.
        Finally, the `timeline` list is assigned to `self.timeline` and returned.

        Returns:
            list: The generated timeline consisting of events extracted from the texts.
        """
        timeline = []
        for text in self.texts:
            page_events = self.get_events(text.page_content)
            for e in page_events:
                e["source"] = text.page_content
                e["page"] = text.metadata["page"] + 1
            timeline = timeline + page_events
        self.timeline = timeline
        return timeline

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
        head = """
        <link rel="stylesheet" href="https://unpkg.com/d3-milestones/build/d3-milestones.css">
        <script src="https://unpkg.com/d3-milestones/build/d3-milestones.min.js"></script>
        <div id="tooltip"
        style="position: absolute; opacity: 0; padding: 10px; background-color: whitesmoke; border: 1px solid black; border-radius: 5px; width:300px; font-size: 8pt;">
        </div>
        """

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
        .onEventClick((d) => {
            window.open('"""

        script = script + self.pdf_name

        script = (
            script
            + """#page=' + d.srcElement.__data__.attributes.page, '_blank');
        })
        .render([
        """
        )
        js_string = [
            {"year": "{}/1/1".format(start_year), "title": "Start of timeline"}
        ]
        for e in self.timeline:
            if e["year"] > start_year and e["year"] < end_year:
                js_string.append(
                    {
                        "year": "{}/{}/{}".format(
                            e["year"],
                            1,
                            1,
                            # max(1, int(e["month"])),
                            # max(1, int(e["day_of_month"])),
                        ),
                        "title": (
                            e["event"] + " (year level)"
                            if e["month"] == 0
                            else e["event"]
                        ),
                        "page": e["page"],
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

    def get_events(self, text):
        """
        Extracts a timeline with dates from the given text and returns it as a list of event objects.

        Args:
            text (str): The text from which to extract the timeline.

        Returns:
            list: A list of event objects, where each event has the attributes "year", "month", "day of month", and "event".
                  If the month and day of month are unknown, they will be left blank.

        Raises:
            ValueError: If the response from the language model is not in a valid JSON format.

        """
        template = """
        Extract a timeline with dates from the text given below. The timeline should be stored in json as an array
        of event objects where each event has the attributes "year", "month", "day_of_month" and "event". If the month and day
        of month are unknown then they should be left blank. When a person's name is followed by two dates in brackets then 
        the first date is the birth date and the second date is the death date. You should include both the birth and the death
        in the timeline. For example, "Albert Einstein (1879-1955)" should be included as two events, one for the birth and one
        for the death.
        Here is the text: {page}.
        """

        prompt = PromptTemplate(template=template, input_variables=["page"])
        llm_chain = LLMChain(
            prompt=prompt, llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        )
        response = llm_chain.run({"page": text})

        response = response.replace("```json", "").replace("```", "").strip()

        try:
            # Read the response as a json object
            response = json.loads(response)
        except ValueError:
            raise ValueError("Error reading response as json")

        # Check the overall format of the response
        if self.check_format(response) is False:
            # Raise a warning and return an empty list
            print("Invalid format")
            return []

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
        }

        # Transform the response
        for e in response:
            if e["month"] != "":
                if str(e["month"]).lower() in month_map:
                    e["month"] = month_map[e["month"].lower()]
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
                e["year"] = 0

        # Filter the response

        clean_events = []
        for e in response:
            if self.validate_event(e):
                clean_events.append(e)

        return clean_events

    @staticmethod
    def validate_event(event):
        # Check that year is an integer
        if event["year"] == 0:
            return False
        return True

    def check_format(self, events):

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

    def filter_events(self, events):
        clean_events = []
        for e in events:
            if self.validate_event(e):
                clean_events.append(e)
        return clean_events
