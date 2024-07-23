import time
import asyncio
import json
from typing import Union
from dotenv import load_dotenv
import os

import aiofiles
import requests
from eth_typing import ChecksumAddress, Address
from faker import Faker
from loguru import logger

from ClashAPI import *

# 加载.env文件
load_dotenv()
client_key = os.getenv('client_key')

# 配置
base_url = "http://127.0.0.1:9090"
secret = "vRH-89R-3Dx-vrc"
api = ClashAPI(base_url, secret)

used_proxies = set()
used_ips = set()

fake = Faker()

def load_used_proxies():
    try:
        with open('used_proxies.txt', 'r') as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_used_proxies(proxies):
    with open('used_proxies.txt', 'w') as f:
        f.write('\n'.join(proxies))

def load_used_ips():
    try:
        with open('used_ips.txt', 'r') as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_used_ips(ips):
    with open('used_ips.txt', 'w') as f:
        f.write('\n'.join(ips))

used_proxies = load_used_proxies()
used_ips = load_used_ips()

def get_yescaptcha_turnstile_token():
    logger.warning("Going to take money form you account.")
    print("going to check the IP in get_yescaptcha_turnstile_token, should be the same.")
    is_proxy_working()
    json_data = {"clientKey": client_key,
                 "task": {"websiteURL": "https://bartio.faucet.berachain.com/",
                          "websiteKey": "0x4AAAAAAARdAuciFArKhVwt",
                          "type": "TurnstileTaskProxylessM1"}, "softID": 109}
    try:
        response = requests.post('https://api.yescaptcha.com/createTask', json=json_data)
        response_json = response.json()
        if response_json['errorId'] != 0:
            logger.warning(response_json)
            return False
        task_id = response_json['taskId']
    except Exception as e:
        print(e)
        return False

    for _ in range(120):
        try:
            data = {"clientKey": client_key, "taskId": task_id}
            response = requests.post('https://api.yescaptcha.com/getTaskResult', json=data)
            response_json = response.json()
            logger.warning("response_json from yescap is", response_json)
            if response_json['status'] == 'ready':
                return response_json['solution']['token']
            else:
                time.sleep(1)
        except Exception as e:
            print(e)

    return False

def write_to_file(address: Union[Address, ChecksumAddress]):
    with open('claim_success.txt', 'a+') as f:
        f.write(f'{address}\n')


def read_to_file(file_path: str):
    with open('claim_success.txt', 'r') as success_file:
        claim_success = success_file.read().splitlines()

    with open(file_path, 'r') as file:
        lines = file.readlines()
    claim_list = [_address.strip() for _address in lines if _address.strip() not in claim_success]

    return claim_list


def claim_faucet(address: Union[Address, ChecksumAddress], google_token: str) -> bool:
    logger.warning(f"Going to claim_faucet now. token is {google_token}")
    user_agent = fake.chrome()
    headers = {'authorization': f'Bearer {google_token}',
               'origin': 'https://bartio.faucet.berachain.com',
               'referer': 'https://bartio.faucet.berachain.com/',
               'user-agent': user_agent}
    params = {'address': address}
    print("going to check the IP in claim_faucet, should be the same.")
    is_proxy_working()

    for attempt in range(5):  # Try up to 5 times
        try:
            response = requests.post('https://bartio-faucet.berachain-devnet.com/api/claim', headers=headers,
                                 data=json.dumps(params), params=params)
            response_text = response.text
            print("claim_faucet response_text:", response_text)

            if 'Added' in response_text:
                logger.success(response_text)
                write_to_file(address)
                return True
            else:
                logger.warning(response_text.replace('\n', ''))
                time.sleep(2)  # Wait before the next attempt
        except Exception as e:
            print(e)  
            time.sleep(1)      
        
    return False  # Return False if all attempts fail

def claim(address: Union[Address, ChecksumAddress]) -> bool:
    google_token = get_yescaptcha_turnstile_token()
    print("google_token", google_token)
    if google_token:
        claim_result = claim_faucet(address, google_token)
        return claim_result


async def run(file_path):
    #sem = asyncio.Semaphore(max_concurrent)
    address_list = read_to_file(file_path)

    async def claim_wrapper(address):
        logger.info(f"Going to claim for address: {address}")
        claim_result = claim(address)
        logger.info(f"Done for {address}, result is {claim_result}")
        return claim_result

    for address in address_list:
        switch_result = select_proxy()
        if switch_result:
            claim_result = await claim_wrapper(address)
            if claim_result:
                logger.success(f"Got money for address: {address}")


import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_url(url):
    try:
        response = requests.get(url, timeout=5)  # 将超时时间减少到5秒
        if response.status_code == 200:
            ip_address = response.json().get("ip")
            return ip_address
    except requests.RequestException:
        pass
    return None

def is_proxy_working():
    test_urls = [
        "https://ipinfo.io/json",
        "https://ipwhois.app/json/",
        "https://api.ipify.org?format=json"
    ]

    with ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(fetch_url, url): url for url in test_urls}
        for future in as_completed(future_to_url):
            ip_address = future.result()
            if ip_address:
                print(f"Current IP address: {ip_address}")
                return ip_address
    
    print("All test URLs failed.")
    return False


def select_proxy():
    global used_proxies, used_ips
    selectors = api.get_selector_list()
    selector_index = 1
    selector = selectors[selector_index - 1] if 0 < selector_index <= len(selectors) else None
    if selector:
        response = api.clash_request(f"{api.base_url}/proxies")
        proxies = response.json()["proxies"][selector]["all"]

        # Determine the starting index based on the last used proxy
        if used_proxies:
            last_used_proxy = list(used_proxies)[-1]
            start_index = proxies.index(last_used_proxy) + 1 if last_used_proxy in proxies else 3
        else:
            start_index = 3

        # Iterate through proxies starting from the determined index
        for i in range(start_index, len(proxies)):
            proxy = proxies[i]
            if proxy not in used_proxies:
                print(f"Switching to proxy: {proxy} for selector: {selector}")
                try:
                    api.switch_proxy(selector, proxy)
                    print("Going to check the IP in select proxy, the first time of this IP.")
                    ip_address = is_proxy_working()
                    if ip_address and ip_address not in used_ips:
                        used_proxies.add(proxy)
                        used_ips.add(ip_address)
                        save_used_proxies(used_proxies)
                        save_used_ips(used_ips)
                        print(f"Proxy {proxy} with IP {ip_address} is working")
                        return True
                    else:
                        print(f"Proxy {proxy} with IP {ip_address} is not working or IP is already used")
                except Exception as e:
                    print(f"Error switching proxy: {e}")
                    continue

        # If no proxies were found from the starting index, iterate from the beginning
        for i in range(3, start_index):
            proxy = proxies[i]
            if proxy not in used_proxies:
                print(f"Switching to proxy: {proxy} for selector: {selector}")
                try:
                    api.switch_proxy(selector, proxy)
                    print("Going to check the IP in select proxy, the first time of this IP.")
                    ip_address = is_proxy_working()
                    if ip_address and ip_address not in used_ips:
                        used_proxies.add(proxy)
                        used_ips.add(ip_address)
                        save_used_proxies(used_proxies)
                        save_used_ips(used_ips)
                        print(f"Proxy {proxy} with IP {ip_address} is working")
                        return True
                    else:
                        print(f"Proxy {proxy} with IP {ip_address} is not working or IP is already used")
                except Exception as e:
                    print(f"Error switching proxy: {e}")
                    continue
        
        print("No available proxies found.")
        return False
    else:
        return False



def reset_and_run():
    global used_proxies, used_ips
    #save_used_proxies(used_proxies)
    #save_used_ips(used_ips)
    with open('claim_success.txt', 'r') as f:
        claim_success_addresses = f.read().splitlines()
    with open('address.txt', 'r') as f:
        address_addresses = f.read().splitlines()
    if set(claim_success_addresses) == set(address_addresses):
        with open('claim_success.txt', 'w') as f:
            f.truncate(0)
    _file_path = 'address.txt'
    asyncio.run(run(_file_path))

if __name__ == '__main__':
    # 验证平台key
    
    # 目前支持使用yescaptcha 2captcha
    solver_provider = 'yescaptcha'
    # 并发数量
    # 读取文件的路径 地址一行一个
    while True:
        #time.sleep(8 * 60 * 60 + 30 * 60)  # 每8小时30分钟重置并重新运行

        reset_and_run()
