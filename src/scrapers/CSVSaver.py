import csv

class CarDataWriter:
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.writer = None

    def initialize(self):
        print("Initializing CSV file...")
        self.file = open(self.filename, 'w', newline='')
        self.writer = csv.DictWriter(self.file, fieldnames=[
            'Manufacturer', 'Model', 'Year', 'Registration Status', 'Price', 'Mileage',
            'Keys', 'Damage description', 'Transmission', 'Seats', 'Fuel Type', 'Link'
        ])
        self.writer.writeheader()

    def save_entry(self, data, entry_number):
        print("Saving entry..." + str(entry_number))
        self.writer.writerow(data)
        self.file.flush()

    def wrap_up(self):
        print("Wrapping up CSV file...")
        self.file.close()

# Example usage:
if __name__ == '__main__':
    writer = CarDataWriter('car_data.csv')
    writer.initialize()

    # Example data
    car_data = {
        'Manufacturer': 'Ford',
        'Model': 'Mustang',
        'Year': '2020',
        'Registration Status': 'Registered',
        'Price': 25000,
        'Mileage': 50000,
        'Keys': 2,
        'Damage description': 'Minor scratches on the bumper',
        'Transmission': 'Automatic',
        'Seats': 4,
        'Fuel Type': 'Gasoline'
    }

    writer.save_entry(car_data)
    writer.wrap_up()
