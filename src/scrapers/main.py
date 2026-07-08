from calendar import c
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from ScrapeVehiclePage import scrape_vehicle_page
from CSVSaver import CarDataWriter
from PageLengthFinder import count_number_of_pages
import json
import datetime
import os
import time
from pathlib import Path

# Get today's date
today = datetime.date.today()

# Ensure data/raw directory exists
data_dir = Path(__file__).parent.parent.parent / "data" / "raw"
data_dir.mkdir(parents=True, exist_ok=True)

# Create the filename with today's date in data/raw/
filename = data_dir / f"car_data_{today}.csv"

# Create an instance of CarDataWriter with the filename
writer = CarDataWriter(str(filename))
writer.initialize()

url = "https://manheim.co.nz/damaged-vehicles/search?PageNumber=1&RecordsPerPage={}&searchType=Z&page={}"

numberOfEntries = 120  # Specify the value of N here
current_page = 1 # Specify the value of page here

# Format the URL with the values of N and page
formatted_url = url.format(numberOfEntries, current_page)

# Headers to mimic a real browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://manheim.co.nz/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin'
}

# Create a session to persist cookies
session = requests.Session()
session.headers.update(headers)

number_of_pages = count_number_of_pages(formatted_url)

while current_page <= number_of_pages:
    
    # Add delay between pages to avoid rate limiting
    if current_page > 1:
        time.sleep(2)
    
    # Send a GET request to the formatted_url with retry logic
    max_retries = 3
    response = None
    for attempt in range(max_retries):
        try:
            response = session.get(formatted_url, timeout=30)
            if response.status_code == 200:
                break
            elif attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"Page {current_page} got status {response.status_code}, retrying in {wait_time}s...")
                time.sleep(wait_time)
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"Page {current_page} request failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Failed to fetch page {current_page} after {max_retries} attempts")
                writer.wrap_up()
                exit(1)
    
    if not response or response.status_code != 200:
        print(f"Failed to fetch page {current_page}, skipping...")
        current_page += 1
        formatted_url = url.format(numberOfEntries, current_page)
        continue

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the section with class "vehicle-list"
    vehicle_list_section = soup.find("section", class_="vehicle-list")

    # Find all the <li> elements with class "vehicle-item"
    list_items = vehicle_list_section.find_all("li", class_="vehicle-item")

    def extract_year_from_link(link):
        """Extract the vehicle year from the link URL.
        Example: /000000000006640234/2004-nissan-... -> 2004"""
        match = re.search(r'/(\d{4})-', link)
        return match.group(1) if match else 'N/A'

    def return_JSON_values(json_data, parameter):
        data = json.loads(json_data)
        details = data['Vehicle Details']
        info = data['Vehicle Info']
        damage = data['Vehicle Damage']
        comments = data['Vehicle Comments']

        if parameter == "Odometer":
            odometer = details[details.find("Odometer")+len("Odometer, "):details.find(" KM Showing")] if details.find("Odometer") != -1 else "N/A"
            return odometer
        
        elif parameter == "Transmission":
            transmission = details[details.find("Transmission")+len("Transmission, "):details.find(" Engine")] if details.find("Transmission") != -1 else "N/A"
            return transmission
        
        elif parameter == "Make":
            make = details[details.find("Make") + len("Make, "):details.find(",", details.find("Make") + len("Make, "))].strip() if details.find("Make") != -1 else "N/A"
            return make
        
        elif parameter == "Model":
            model = details[details.find("Model") + len("Model, "):details.find(",", details.find("Model") + len("Model, "))].strip() if details.find("Model") != -1 else "N/A"
            return model
        
        elif parameter == "Seats":
            seats = details[details.find("Seats") + len("Seats, "):details.find(",", details.find("Seats") + len("Seats, "))].strip() if details.find("Seats") != -1 else "N/A"
            return seats
        elif parameter == "Fuel Type":
            fuel_type = details[details.find("Fuel Type") + len("Fuel Type, "):].strip() if details.find("Fuel Type") != -1 else "N/A"
            return fuel_type
        
        elif parameter == "No of Keys":
            keys = info[info.find("No of Keys")+len("No of Keys, "):info.find(",",info.find("No of Keys")+ len("No of Keys, "))].strip() if info.find("No of Keys") != -1 else "N/A"
            return keys
        
        elif parameter == "Damage Description":
            damage = damage[damage.find(",")+1:]
            return damage   
        
        elif parameter == "Registration Status":
            # Check both comments AND damage description for registration status
            # Check for De-Registered first to avoid substring matching issue
            combined_text = comments + " " + damage
            if "Selling De-Registered" in combined_text or "De-Registered" in combined_text:
                registered = "No"
            elif "Selling Registered" in combined_text:
                registered = "Yes"
            else:
                registered = "No"
            return registered
        
        else:
            return "N/A"

    try:
        current_entry = 1
        # Iterate over each <li> element
        for item in list_items:
            # Find the value of class "vehicle"
            vehicle = item.find(class_="vehicle").get_text(strip=True)

            # Find the header with class "card-header"
            header = item.find(class_="card-header")
            
            # Find the <a> tag within the header
            a_tag = header.find("a")
            href = urljoin(url, a_tag["href"]) if a_tag and "href" in a_tag.attrs else "N/A"
            
            # Find the span with the corresponding ID
            span_id = item.find("span", id=lambda value: value and value.startswith("stprice-"))
            price = span_id.get_text(strip=True) if span_id else "N/A"

            # Call the scrape_vehicle_page() function from ScrapeVehiclePage.py
            # Add small delay between vehicle page requests
            time.sleep(0.5)
            json_data = scrape_vehicle_page(href)
            
            # Display the results
            # print("Vehicle:", vehicle)
            # print("Href:", href)
            # print("Price:", price)
            # print("JSON Data:")
            # print(json_data)
            # print("-------------------------")
            car_data = {
                'Manufacturer': return_JSON_values(json_data, "Make"),
                'Model': return_JSON_values(json_data, "Model"),
                'Year': extract_year_from_link(href),
                'Registration Status': return_JSON_values(json_data, "Registration Status"),
                'Price': price,
                'Mileage': return_JSON_values(json_data, "Odometer"),
                'Keys': return_JSON_values(json_data, "No of Keys"),
                'Damage description': return_JSON_values(json_data, "Damage Description"),
                'Transmission': return_JSON_values(json_data, "Transmission"),
                'Seats': return_JSON_values(json_data, "Seats"),
                'Fuel Type': return_JSON_values(json_data, "Fuel Type"),
                'Link': href,
            }
            # Get the values and convert them to strings, replacing commas with colons
            values = [str(value).replace(',', ':') for key, value in car_data.items() if key != 'Damage description']
            # Join the values with commas
            csv_line = ', '.join(values)
            print(csv_line)

            writer.save_entry(car_data, ((current_page-1)*numberOfEntries)+current_entry)
            current_entry += 1

    except Exception as exception:
        print("An error occurred. Program crashed." + exception)
        writer.wrap_up()          

    #end of while loop
    current_page += 1
    formatted_url = url.format(numberOfEntries, current_page)
    print("Page {} of {} completed".format(current_page, number_of_pages))


# Wrap up the CSV file writing process
writer.wrap_up()
print("Program completed successfully.")


