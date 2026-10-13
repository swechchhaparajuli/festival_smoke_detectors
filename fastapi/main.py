import json
import datetime
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

## These are our collectors: 
from collectors.epa_collector import * 
from collectors.noaa_collector import *
from collectors.wikipedia_scraper import * 

## the transform.py will transform the data into once document before we can store it into gcs 
from transform import *

## storage - we can call the function inside storage.py 
from storage import *


from pydantic import BaseModel

from user_definition import *


app = FastAPI()

# On first start of the app -- the transform and storage functions are run so that all of the data is reloaded

@app.post("/load_data")
def load_data():
    """
    Use 

    TODO:
    1. Split search_input.company_dict into two groups: the "Anthropic"
       entry (if present) and everything else.
    2. For EPA, the code should go to the corresponding value of
       `festival`, .
       Extract the information including title, and URL,
       and call qualification_parser to get qualification.
       (optional) To improve performance you can try the asynchronous version.
    3. Build up a single festival_data_response dict incrementally: start it
       empty, add Wikipedia results first (if any), then call
       noa for the noaa data, then call epa_collector for the epa data.
    5. Save the combined data to GCS the same way HW3 did.
    """


    ### call transform for all types 

    ### put the cleaned data together into one json/object etc
    
    ### call storage / store this combined document


    pass



