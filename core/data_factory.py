"""
Test Data Factory Module
Generates realistic test data using Faker library
"""
from faker import Faker
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class DataFactory:
    """
    Generates realistic test data for API testing.
    """
    
    def __init__(self, locale: str = "en_US"):
        """
        Initialize data factory.
        
        Args:
            locale: Locale for generated data (default: en_US)
        """
        self.fake = Faker(locale)
        self._last_generated = None
    
    # Person Data
    def generate_name(self) -> str:
        """Generate random full name"""
        self._last_generated = self.fake.name()
        return self._last_generated
    
    def generate_first_name(self) -> str:
        """Generate random first name"""
        self._last_generated = self.fake.first_name()
        return self._last_generated
    
    def generate_last_name(self) -> str:
        """Generate random last name"""
        self._last_generated = self.fake.last_name()
        return self._last_generated
    
    def generate_email(self) -> str:
        """Generate random email address"""
        self._last_generated = self.fake.email()
        return self._last_generated
    
    def generate_phone(self) -> str:
        """Generate random phone number"""
        self._last_generated = self.fake.phone_number()
        return self._last_generated
    
    def generate_ssn(self) -> str:
        """Generate random SSN"""
        self._last_generated = self.fake.ssn()
        return self._last_generated
    
    # Address Data
    def generate_address(self) -> str:
        """Generate random street address"""
        self._last_generated = self.fake.street_address()
        return self._last_generated
    
    def generate_city(self) -> str:
        """Generate random city name"""
        self._last_generated = self.fake.city()
        return self._last_generated
    
    def generate_state(self) -> str:
        """Generate random state name"""
        self._last_generated = self.fake.state()
        return self._last_generated
    
    def generate_zipcode(self) -> str:
        """Generate random ZIP code"""
        self._last_generated = self.fake.zipcode()
        return self._last_generated
    
    def generate_country(self) -> str:
        """Generate random country name"""
        self._last_generated = self.fake.country()
        return self._last_generated
    
    # Internet Data
    def generate_username(self) -> str:
        """Generate random username"""
        self._last_generated = self.fake.user_name()
        return self._last_generated
    
    def generate_password(self, length: int = 12) -> str:
        """Generate random password"""
        self._last_generated = self.fake.password(length=length)
        return self._last_generated
    
    def generate_url(self) -> str:
        """Generate random URL"""
        self._last_generated = self.fake.url()
        return self._last_generated
    
    def generate_ipv4(self) -> str:
        """Generate random IPv4 address"""
        self._last_generated = self.fake.ipv4()
        return self._last_generated
    
    def generate_mac_address(self) -> str:
        """Generate random MAC address"""
        self._last_generated = self.fake.mac_address()
        return self._last_generated
    
    # Company Data
    def generate_company_name(self) -> str:
        """Generate random company name"""
        self._last_generated = self.fake.company()
        return self._last_generated
    
    def generate_job_title(self) -> str:
        """Generate random job title"""
        self._last_generated = self.fake.job()
        return self._last_generated
    
    # Financial Data
    def generate_credit_card_number(self) -> str:
        """Generate random credit card number"""
        self._last_generated = self.fake.credit_card_number()
        return self._last_generated
    
    def generate_iban(self) -> str:
        """Generate random IBAN"""
        self._last_generated = self.fake.iban()
        return self._last_generated
    
    def generate_currency_code(self) -> str:
        """Generate random currency code"""
        self._last_generated = self.fake.currency_code()
        return self._last_generated
    
    # Date/Time Data
    def generate_date(self, start_date: str = "-30y", end_date: str = "today") -> str:
        """Generate random date"""
        date = self.fake.date_between(start_date=start_date, end_date=end_date)
        self._last_generated = date.strftime("%Y-%m-%d")
        return self._last_generated
    
    def generate_datetime(self) -> str:
        """Generate random datetime"""
        dt = self.fake.date_time_this_year()
        self._last_generated = dt.strftime("%Y-%m-%d %H:%M:%S")
        return self._last_generated
    
    def generate_future_date(self, days: int = 30) -> str:
        """Generate future date"""
        date = self.fake.future_date(end_date=f"+{days}d")
        self._last_generated = date.strftime("%Y-%m-%d")
        return self._last_generated
    
    def generate_past_date(self, days: int = 30) -> str:
        """Generate past date"""
        date = self.fake.past_date(start_date=f"-{days}d")
        self._last_generated = date.strftime("%Y-%m-%d")
        return self._last_generated
    
    # Identifier Data
    def generate_uuid(self) -> str:
        """Generate random UUID"""
        self._last_generated = str(uuid.uuid4())
        return self._last_generated
    
    def generate_alphanumeric(self, length: int = 10) -> str:
        """Generate random alphanumeric string"""
        self._last_generated = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        return self._last_generated
    
    def generate_numeric(self, length: int = 10) -> str:
        """Generate random numeric string"""
        self._last_generated = ''.join(random.choices(string.digits, k=length))
        return self._last_generated
    
    # Text Data
    def generate_sentence(self, words: int = 10) -> str:
        """Generate random sentence"""
        self._last_generated = self.fake.sentence(nb_words=words)
        return self._last_generated
    
    def generate_paragraph(self, sentences: int = 3) -> str:
        """Generate random paragraph"""
        self._last_generated = self.fake.paragraph(nb_sentences=sentences)
        return self._last_generated
    
    def generate_text(self, max_chars: int = 200) -> str:
        """Generate random text"""
        self._last_generated = self.fake.text(max_nb_chars=max_chars)
        return self._last_generated
    
    # Numeric Data
    def generate_random_int(self, min: int = 1, max: int = 100) -> int:
        """Generate random integer"""
        self._last_generated = random.randint(min, max)
        return self._last_generated
    
    def generate_random_float(self, min: float = 0.0, max: float = 100.0, decimals: int = 2) -> float:
        """Generate random float"""
        value = random.uniform(min, max)
        self._last_generated = round(value, decimals)
        return self._last_generated
    
    # Boolean Data
    def generate_boolean(self) -> bool:
        """Generate random boolean"""
        self._last_generated = self.fake.boolean()
        return self._last_generated
    
    # Complex Data
    def generate_user_profile(self) -> Dict:
        """Generate complete user profile"""
        profile = {
            "id": self.generate_uuid(),
            "username": self.generate_username(),
            "email": self.generate_email(),
            "first_name": self.generate_first_name(),
            "last_name": self.generate_last_name(),
            "phone": self.generate_phone(),
            "date_of_birth": self.generate_date(start_date="-65y", end_date="-18y"),
            "address": {
                "street": self.generate_address(),
                "city": self.generate_city(),
                "state": self.generate_state(),
                "zipcode": self.generate_zipcode(),
                "country": self.generate_country()
            },
            "company": self.generate_company_name(),
            "job_title": self.generate_job_title(),
            "created_at": self.generate_datetime()
        }
        self._last_generated = profile
        return profile
    
    def generate_transaction(self) -> Dict:
        """Generate financial transaction data"""
        transaction = {
            "transaction_id": self.generate_uuid(),
            "amount": self.generate_random_float(1.0, 10000.0, 2),
            "currency": self.generate_currency_code(),
            "timestamp": self.generate_datetime(),
            "description": self.generate_sentence(5),
            "status": random.choice(["pending", "completed", "failed"]),
            "from_account": self.generate_iban(),
            "to_account": self.generate_iban()
        }
        self._last_generated = transaction
        return transaction
    
    # Utility Methods
    def last_generated_value(self) -> any:
        """Get the last generated value"""
        return self._last_generated
    
    def generate_list(self, generator_method: str, count: int) -> List:
        """
        Generate list of values using specified generator method.
        
        Args:
            generator_method: Name of generator method (e.g., 'generate_email')
            count: Number of items to generate
            
        Returns:
            List of generated values
        """
        if not hasattr(self, generator_method):
            raise ValueError(f"Unknown generator method: {generator_method}")
        
        generator = getattr(self, generator_method)
        return [generator() for _ in range(count)]


# Global instance for convenience
_data_factory = DataFactory()


def get_data_factory() -> DataFactory:
    """Get global data factory instance"""
    return _data_factory
