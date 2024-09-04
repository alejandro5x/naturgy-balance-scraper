import re
from playwright.sync_api import Playwright, sync_playwright, expect, TimeoutError
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
import time
import paho.mqtt.client as mqtt
import os
import json

load_dotenv()
naturgy_number = os.getenv('NATURGY_NUMBER')
naturgy_password = os.getenv('NATURGY_PASSWORD')
mqtt_user = os.getenv('MQTT_USER')
mqtt_password = os.getenv('MQTT_PASSWORD')
mqtt_server = os.getenv('MQTT_BROKER')
mqtt_port = int(os.getenv('MQTT_PORT'))
mqtt_topic = os.getenv('NATURGY_MQTT_TOPIC')
mqtt_error_topic = os.getenv('NATURGY_MQTT_ERROR_TOPIC')  # Separate Topic for errors

def run(playwright: Playwright) -> None:

    #browser = playwright.chromium.launch(headless=False, slow_mo=50)
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://clientes.naturgy.com.pa/oficinavirtual/")

    try:
        page.locator("[id=\"loginForm\\:userName\"]").click()
        page.locator("[id=\"loginForm\\:userName\"]").fill(naturgy_number)
        page.locator("[id=\"loginForm\\:userName\"]").press("Tab")
        page.locator("[id=\"loginForm\\:password\"]").click()
        page.locator("[id=\"loginForm\\:password\"]").fill(naturgy_password)
        page.get_by_role("button", name="Entrar").click()
        #page.goto("https://clientes.naturgy.com.pa/oficinavirtual/home.xhtml")
        page.get_by_role("link", name="Mis facturas").click()

        # Getting balance
        html = page.inner_html('#j_idt184')
        soup = BeautifulSoup(html, 'html.parser')
        #print(soup.td.text)
        balance = float(soup.td.text)

        #balance = balance_element.replace("B/. ", "")
        send_mqtt_data(mqtt_server, mqtt_port, mqtt_user, mqtt_password, mqtt_topic, balance)
        send_mqtt_error(mqtt_server, mqtt_port, mqtt_user, mqtt_password, mqtt_error_topic, "")
    except (TimeoutError, ValueError) as e:
        error_message = f"Error getting balance: {str(e)}"
        print(error_message)
        send_mqtt_error(mqtt_server, mqtt_port, mqtt_user, mqtt_password, mqtt_error_topic, error_message)
        balance = "Error"
    finally:
        context.close()
        browser.close()


def send_mqtt_data(server, port, user, password, topic, balance):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, mqtt_user)
    client.username_pw_set(user, password)
    client.connect(server, port)
    client.loop_start()

    xpayload = json.dumps({
        "state": str(balance),
        "updated_ts": str(int(time.time())),
        "updated_dt": str(datetime.now())
    }, sort_keys=True, default=str)

    client.publish(topic=topic, payload=xpayload, qos=0, retain=False)
    time.sleep(1)
    client.loop_stop()

def send_mqtt_error(server, port, user, password, topic, error_message):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, mqtt_user)
    client.username_pw_set(user, password)
    client.connect(server, port)
    client.loop_start()

    xpayload = json.dumps({
        "error": error_message,
        "updated_ts": str(int(time.time())),
        "updated_dt": str(datetime.now())
    }, sort_keys=True, default=str)

    client.publish(topic=topic, payload=xpayload, qos=0, retain=False)
    time.sleep(1)
    client.loop_stop()

with sync_playwright() as playwright:
    run(playwright)
