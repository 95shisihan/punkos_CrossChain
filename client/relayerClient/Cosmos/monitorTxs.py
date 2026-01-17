import requests

url = 'https://cosmos-rpc.polkachu.com/tx?hash=0x302B6A428ACF3068D9E2DA240E275C41DF96B1A633ED11C96B196A2D6932FE76'
headers = {
    'Content-Type': 'application/json'
}

response = requests.get(url, headers=headers)
data = response.json()

# 处理响应数据
print(data)
