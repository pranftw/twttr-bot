# twttr_bot
Twitter Bot implemented with Python

# Installation

`git clone repo` <br>
`cd repo` <br>
create and activate virtual env <br>
`pip install -r requirements.txt` <br>

- For Streaming <br>
  `cd src` <br>
  `cp ../config.py.example config.py`<br>
  Fill in the necessary details in config.py<br>
  `python -m src.bot` <br>
  ctrl + c to kill the streaming <br>

- For Scraping <br>
  `cd ..;cd scraper` <br>
  `cp ../extracted_data.json.example extracted_data.json && cp ../extracted_data.json.example hashed_data.json`<br>
  set your queries in scraper_config.py <br>
  `python -m scraper.scraper <number of tweets>` <br>
