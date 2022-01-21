# Notifier API
This is a django REST framework powered API to send notifications to users using the Twilio and SendGrid APIs.  After logging in using Django's built in user authentication system, users can update their preferences to email, sms, or none, and send notifications at a time of their choosing.

## Requirements
Sign up for Twilio API and SendGrid API.

## Environment
There are 3 services that need to run:
* django REST API server
* celery worker - send scheduled messages asynchronously
* redis - message broker for celery
For either of the setup methods below you will need to define your environment variables:
Create a `.env` file with the following info from your Sendgrid and Twilio accounts:
```
export SENDGRID_FROM_EMAIL=''
export SENDGRID_API_KEY=''
export TWILIO_ACCOUNT_SID=''
export TWILIO_AUTH=''
export TWILIO_MESSAGING_SERVICE_SID=''
export DJANGO_SECRET_KEY=''
```

### Setup
This setup runs all 4 processes in different terminal windows using a venv.  

Create a virtualenv and install the necessary packages:
```
$ virtualenv -p 3.7 venv
$ pip install -r requirements.txt
```

Then source the `.env` file to load the variables into your environment as shown in steps 1 and 3.  These are loaded into the application in `settings.py`

1. Run a redis server with the default settings
```
brew install redis
redis-server
```
2. Run the celery worker
```
. venv/bin/activate
source .env
celery -A notificationapi worker -l INFO
```
3. Run the PostgreSQL database
**Option 1 - docker-compose:**
Install the docker daemon (e.g. Docker for Mac)
Run the docker daemon
```
docker-compose up
```
**Option 2 - Manually:**
```
brew install postgres
pg_ctl -D pgdata init
pg_ctl -D pgdata -l logfile start
psql
# inside psql shell make the following queries
CREATE USER notifier WITH PASSWORD 'password';
CREATE DATABASE notifier;
GRANT ALL PRIVILEGES ON DATABASE notifier TO notifier;
\q
```

4. Create a user and Run the django webserver
```
cd notificationapi
. venv/bin/activate
source .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

# API Use Instructions
With the 3 services above running, navigate to http://localhost:8000
Login with the user created in Manual setup using the button in the top right.
Use the [Notifier API Postman Collection](https://documenter.getpostman.com/view/10758113/U16gRT8j) for testing the API

## GET http://{host}/preference/
Returns information from on the logged in user and the user preferences

**Response:**
* username - The currently logged in user
* notify_pref - "email", "sms", or "None"
* email
* phone - Integer formatted phone number including country and area code
Example:
```
curl -u user:password --location --request POST 'http://localhost:8000/preference/'
```

## POST http://{host}/preference/
Changes the user's notification preferences in the database. 
Not including notify_pref will leave it unchanged.
Email and sms fields are not required so users can omit their email address if their preference is sms and vice versa.

**Request:**
Include the following preferences in json format in the body of your request
* notify_pref (optional) - "email"(default), "sms", or "None"
* email (optional)
* phone (optional) - Integer formatted phone number including country and area code

**Response:**
Updated values for the user's preferences
* username - The currently logged in user
* notify_pref - "email", "sms", or "None"
* email
* phone - Integer formatted phone number including country and area code

Example:
```
curl -u user:password --location --request POST 'http://localhost:8000/preference/' \
--header 'Content-Type: application/json' \
--data-raw '{
    "notify_pref": "sms",
    "email": "guy@example.com",
    "phone": 15105552054
}'
```
Example Response:
```
{
    "username": "user"
    "notify_pref": "sms",
    "email": "guy@example.com",
    "phone": 15105552054
}
```

## GET http://{host}/notify/
Returns the same information as GET `/preference/` endpoint for convenience to review user preferences.

## POST http://{host}/notify/
*Note:* To send SMS notifications using the Twilio trial account, the destination phone number must first be validated through the Twilio site.
Sends a notification using the user's preference at the the time specified.

**Request:**
Include the following information in json format in the body of your request
* title (optional) - Subject of the email or first line of the SMS
* text - Body of the email or contents of the SMS
* sendtime (optional) - ISO 8601 formatted datetime e.g. "2021-09-06T15:47:30-07:00" for when the message should be sent.  If this field is omitted or is in the past the message will be sent without delay.

**Response:**
Responds with the same data input plus the email address or phone number depending on the selected preference.  
*Note:* Because messages can be sent at future times, at time of the request we will not know if the message successfully reached its destination or not. So the API will return a successful status code (200) if the request was sucessfully *scheduled* to be sent.
* title (optional) - Subject of the email or first line of the SMS (optional)
* text - Body of the email or contents of the SMS
* sendtime (optional) - datetime of request
* email (if email preference is selected)
* phone (if phone preference is selected)

Example request:
```
curl -u user:password --location --request POST 'http://localhost:8000/notify/' \
--header 'Content-Type: application/json' \
--data-raw '{
    "title": "Subject text example",
    "text": "Body text example",
    "sendtime": "2021-09-06T15:52:10-07:00"
}'
```
Example Response:
```
{
    "title": "Subject text example",
    "text": "Body text example",
    "sendtime": "2021-09-06T22:52:10Z",
    "phone": 15105552054
}
```

## Testing
Automated testing is setup in `tests.py`.  Run these after making any code changes to ensure there are no regression failures using:
```
python manage.py test
```

Notably automated tests for checking messages sent in the future are not present as they are beyond the scope of this project so manual testing was performed for these.
A celery backend is not needed for the app so we can't lookup if the messages succeeded or failed.  One way to set up testing for this would be to set up a test instance of Celery which does include a redis backend.  Then run the trigger_email_task and trigger_sms_task with a future timestamp, sleep in the django test and check that the status changed to succeeded at the correct time.
An absolutely complete test would also include checking the email account and phone account that the messages were actually receive (which was done manually).

## Improvements
Further improvements to this project beyond the scope of an MVP:
* More comprehensive testing as listed above
* Include phone number validation using Twilio Lookup API
* Improved logging 
* docker-compose environment setup
* Switch to a more scalable database choice
* User registration page
* Token authentication
* Handle requests with no user logged in
* Automatically generate docs using drf-spectacular