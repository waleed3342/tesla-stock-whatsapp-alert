import requests
from dotenv import load_dotenv
import os
from twilio.rest import Client
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv("api.env")

STOCK_NAME = "TSLA"
COMPANY_NAME = "Tesla Inc"
ALERT_THRESHOLD = 1
STOCK_ENDPOINT = "https://www.alphavantage.co/query"
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"


def get_stock_data():
    try:
        stock_params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": STOCK_NAME,
            "apikey": os.getenv("STOCK_API_KEY"),
        }

        response = requests.get(STOCK_ENDPOINT, params=stock_params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "Time Series (Daily)" not in data:
            logger.error(f"Unexpected API response: {data}")
            return None

        return data["Time Series (Daily)"]

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching stock data: {e}")
        return None


def calculate_price_change(stock_data):
    try:
        data_list = [value for (key, value) in stock_data.items()]

        yesterday_close = float(data_list[0]["4. close"])
        previous_close = float(data_list[1]["4. close"])

        difference = yesterday_close - previous_close
        percent_change = round((difference / yesterday_close) * 100, 2)

        trend_indicator = "📈" if difference > 0 else "📉" if difference < 0 else "➡️"

        logger.info(f"{STOCK_NAME} price change: {percent_change}%")
        return percent_change, trend_indicator

    except (KeyError, IndexError, ValueError) as e:
        logger.error(f"Error calculating price change: {e}")
        return None, None


def get_news_articles():
    try:
        news_params = {
            "apiKey": os.getenv("NEWS_API_KEY"),
            "qInTitle": COMPANY_NAME,
            "sortBy": "publishedAt",
            "language": "en"
        }

        response = requests.get(NEWS_ENDPOINT, params=news_params, timeout=10)
        response.raise_for_status()

        articles = response.json().get("articles", [])
        return articles[:3]

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching news: {e}")
        return []


def send_whatsapp_alerts(percent_change, trend_indicator, articles):
    try:
        client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))

        from_number = f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}"
        to_number = f"whatsapp:{os.getenv('MY_WHATSAPP_NUMBER')}"

        for article in articles:
            message_body = (
                f"{STOCK_NAME}: {trend_indicator}{percent_change}%\n"
                f"Headline: {article.get('title', 'N/A')}\n"
                f"Brief: {article.get('description', 'N/A')}"
            )

            message = client.messages.create(
                body=message_body,
                from_=from_number,
                to=to_number
            )

            logger.info(f"Message sent: {message.sid}")

    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")


def main():
    logger.info(f"Starting stock alert system for {STOCK_NAME}")

    stock_data = get_stock_data()
    if not stock_data:
        logger.error("Failed to retrieve stock data. Exiting.")
        return

    percent_change, trend_indicator = calculate_price_change(stock_data)
    if percent_change is None:
        logger.error("Failed to calculate price change. Exiting.")
        return

    if abs(percent_change) > ALERT_THRESHOLD:
        logger.info(f"Alert threshold met: {abs(percent_change)}% > {ALERT_THRESHOLD}%")

        articles = get_news_articles()

        if articles:
            send_whatsapp_alerts(percent_change, trend_indicator, articles)
            logger.info("Alerts sent successfully")
        else:
            logger.warning("No news articles found")
    else:
        logger.info(f"No alert needed. Price change: {percent_change}%")


if __name__ == "__main__":
    main()
