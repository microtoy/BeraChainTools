import json

import requests


class ClashAPI:
    def __init__(self, base_url, secret):
        self.base_url = base_url
        self.secret = secret
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.secret}",
        }

    def clash_request(self, url, method="GET", data=None):
        if method == "GET":
            response = requests.get(url, headers=self.headers, timeout = 20)
        elif method == "POST":
            response = requests.post(url, headers=self.headers, data=data)
        elif method == "PUT":
            response = requests.put(url, headers=self.headers, data=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=self.headers, data=data)
        else:
            raise ValueError("Invalid request method.")
        return response

    def get_proxy_list(self):
        response = self.clash_request(f"{self.base_url}/proxies")
        nodes = response.json()["proxies"]
        proxies = [
            proxy["name"]
            for proxy in nodes.values()
            if proxy["type"] == "Shadowsocks" or proxy["type"] == "Vmess"
        ]
        return proxies

    def get_selector_list(self):
        response = self.clash_request(f"{self.base_url}/proxies")
        nodes = response.json()["proxies"]
        selectors = [
            proxy["name"] for proxy in nodes.values() if proxy["type"] == "Selector"
        ]
        return selectors

    def get_mode_list(self):
        modes = ["Rule", "Global"]
        explanations = ["在需要的代理组中切换节点", "在GLOBAL代理组中切换节点"]
        return modes, explanations

    def switch_mode(self, mode):
        # 更新Clash的代理模式设置
        self.clash_request(
            f"{self.base_url}/configs",
            method="PATCH",
            data=json.dumps({"mode": mode}),
        )

    def switch_proxy(self, selector, proxy):
        response = self.clash_request(
            f"{self.base_url}/proxies/{selector}",
            method="PUT",
            data=json.dumps({"name": proxy}),
        )
        if response.status_code == 204:
            print(f"代理节点已更新为：{proxy}")
        elif response.status_code == 400:
            print(f"请求错误：{response.json()}")
        elif response.status_code == 404:
            print(f"未找到代理节点 {proxy}！")

    def get_node_delay(self, proxy):
        response = self.clash_request(f"{self.base_url}/proxies/{proxy}")
        if response.status_code == 200:
            data = response.json()
            name = data["name"]
            delay = data["history"][-1]["delay"]
            print(f"节点 {name} 的延迟为 {delay} ms")
        elif response.status_code == 404:
            print(f"未找到代理节点{proxy}：{response.json()}")
        else:
            print("未知错误")


class ClashMenu:
    def __init__(self, api: ClashAPI):
        self.api = api
        self.functions = {
            "切换代理模式": self.select_mode,
            "切换代理节点": self.select_proxy,
            "获取节点延迟": self.get_delay,
            "获取连接信息": self.get_connections,
            "获取基本配置": self.get_configs,
            "获取代理信息": self.get_proxies,
            "获取规则信息": self.get_rules,
            "获取版本信息": self.get_version,
        }

    def select_mode(self):
        modes, explanations = self.api.get_mode_list()
        print("========== 代理模式列表 ==========")
        for i, mode in enumerate(modes, 1):
            print(f"{i}. {mode}  ({explanations[i-1]})")
        print("===================================")
        mode_index = int(input("请选择代理模式（输入编号）："))
        mode = modes[mode_index - 1] if 0 < mode_index <= len(modes) else None
        if mode:
            self.api.switch_mode(mode)
        else:
            print("无效的选择！")

    def select_proxy(self):
        selectors = self.api.get_selector_list()
        print("========== 代理组列表 ==========")
        for i, selector in enumerate(selectors, 1):
            print(f"{i}. {selector}")
        print("===================================")
        selector_index = int(input("请选择选择器（输入编号）："))
        selector = (
            selectors[selector_index - 1]
            if 0 < selector_index <= len(selectors)
            else None
        )
        if selector:
            response = self.api.clash_request(f"{self.api.base_url}/proxies")
            proxies = response.json()["proxies"][selector]["all"]
            print("========== 代理节点列表 ==========")
            for i, proxy in enumerate(proxies, 1):
                print(f"{i}. {proxy}")
            print(f"[Now]: {response.json()['proxies'][selector]['now']}")
            print("===================================")
            proxy_index = int(input("请选择代理节点（输入编号）："))
            proxy = (
                proxies[proxy_index - 1] if 0 < proxy_index <= len(proxies) else None
            )
            if proxy:
                self.api.switch_proxy(selector, proxy)
            else:
                print("无效的选择！")
        else:
            print("无效的选择！")

    def get_delay(self):
        proxies = self.api.get_proxy_list()
        print("========== 代理节点列表 ==========")
        for i, proxy in enumerate(proxies, 1):
            print(f"{i}. {proxy}")
        print("===================================")
        proxy_index = int(input("请选择代理节点（输入编号）："))
        proxy = proxies[proxy_index - 1] if 0 < proxy_index <= len(proxies) else None
        if proxy:
            self.api.get_node_delay(proxy)
        else:
            print("无效的选择！")

    def get_connections(self):
        response = self.api.clash_request(f"{self.api.base_url}/connections")
        connections = response.json()
        return connections

    def get_configs(self):
        response = self.api.clash_request(f"{self.api.base_url}/configs")
        configs = response.json()
        return configs

    def get_proxies(self):
        response = self.api.clash_request(f"{self.api.base_url}/proxies")
        proxies = response.json()
        return proxies

    def get_rules(self):
        response = self.api.clash_request(f"{self.api.base_url}/rules")
        rules = response.json()
        return rules

    def get_version(self):
        response = self.api.clash_request(f"{self.api.base_url}/version")
        version = response.json()
        return version

    def menu(self):
        while True:
            print("========== Clash功能菜单 ==========")
            for index, function_name in enumerate(self.functions.keys(), start=1):
                print(f"{index}. {function_name}")
            print(f"{len(self.functions) + 1}. 退出菜单")
            print("===================================")
            choice = input("\n请输入选项：")

            if choice.isdigit():
                choice = int(choice)
                if 1 <= choice <= len(self.functions):
                    function_name = list(self.functions.keys())[choice - 1]
                    function_call = self.functions[function_name]
                    print(f"正在执行：{function_name}")
                    response = function_call()
                    if choice > 3:
                        print(f"{function_name} 的响应：{response}")
                elif choice == len(self.functions) + 1:
                    break
                else:
                    print("无效的选项，请重新选择。")
            else:
                print("请输入数字选项。")
            print("\n")


if __name__ == "__main__":
    base_url = "http://127.0.0.1:9090"
    secret = "vRH-89R-3Dx-vrc"
    api = ClashAPI(base_url, secret)
    menu = ClashMenu(api)
    menu.menu()
