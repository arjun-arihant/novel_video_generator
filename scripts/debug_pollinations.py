import requests
import time
import random

def test_get(prompt):
    print(f"Testing GET with prompt length {len(prompt)}...")
    base_url = "https://image.pollinations.ai/prompt/"
    full_url = f"{base_url}{requests.utils.quote(prompt)}"
    params = {
        "model": "flux-anime",
        "width": 1280,
        "height": 720,
        "nologo": "true",
        "enhance": "false",
        "seed": random.randint(1, 10000)
    }
    start = time.time()
    try:
        response = requests.get(full_url, params=params, timeout=30)
        print(f"GET Status: {response.status_code}, Time: {time.time()-start:.2f}s")
        if response.status_code == 200:
            print("GET Success")
        else:
            print(f"GET Failed: {response.text[:200]}")
    except Exception as e:
        print(f"GET Error: {e}")

def test_post(prompt):
    print(f"Testing POST with prompt length {len(prompt)}...")
    url = "https://image.pollinations.ai/prompt/" # or just https://image.pollinations.ai/ ?
    # Docs often imply POST to /prompt might assume prompt in URL, OR verify if it takes body.
    # Actually, many simple APIs support prompt in body.
    # Let's try standard POST structure often used.
    
    # If standard endpoint doesn't support POST, we stick to GET.
    # But let's test if we can send params in body.
    
    # Pollinations doesn't strictly document POST json output clearly on their main landing, 
    # but let's try passing data.
    
    payload = {
        "prompt": prompt,
        "model": "flux-anime",
        "width": 1280,
        "height": 720,
        "nologo": True,
        "enhance": False,
        "seed": random.randint(1, 10000)
    }
    # Often for these APIs, if you POST to /prompt, it might expect prompt in path still?
    # Let's try sending prompt in payload to base URL.
    
    start = time.time()
    try:
        response = requests.post("https://image.pollinations.ai/prompt", json=payload, timeout=30)
        print(f"POST Status: {response.status_code}, Time: {time.time()-start:.2f}s")
        if response.status_code == 200:
            print("POST Success")
            # Verify content type
            print(f"Content Type: {response.headers.get('Content-Type')}")
        else:
            print(f"POST Failed: {response.text[:200]}")
    except Exception as e:
        print(f"POST Error: {e}")

if __name__ == "__main__":
    # Test 1: Simple Prompt
    simple_prompt = "A cute cat in a box"
    # test_get(simple_prompt)
    test_post(simple_prompt) # Testing POST now
    
    print("-" * 20)
    
    # Test 2: Long Manhua Prompt
    long_prompt = "A vertical wide shot of a misty mountain peak in a xianxia world. A cultivator in white robes stands on a flying sword, surrounded by swirling energy/qi. The background features floating islands and cranes. The art style is accurate Chinese Manhua, detailed line art, vibrant blues and whites, cinematic lighting, 8k resolution."
    test_get(long_prompt)
