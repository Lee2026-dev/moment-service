import sys
import uuid
import httpx
import time

def verify_deployment(base_url):
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    
    print(f"🔍 Verifying deployment at: {base_url}")
    
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        print("\n1️⃣  Checking Health (GET /)...")
        try:
            resp = client.get("/")
            resp.raise_for_status()
            print(f"✅ Success: {resp.json()}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            return

        print("\n2️⃣  Checking API Docs (GET /docs)...")
        try:
            resp = client.get("/docs")
            if resp.status_code == 200:
                print("✅ Success: Docs reachable")
            else:
                print(f"⚠️  Warning: Docs returned {resp.status_code}")
        except Exception as e:
            print(f"❌ Failed: {e}")

        print("\n3️⃣  Running Smoke Test (Auth + AI)...")
        email = f"verify_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        
        try:
            print(f"   - Registering temp user: {email}")
            resp = client.post("/auth/register", json={"email": email, "password": password})
            if resp.status_code != 200:
                print(f"   ❌ Registration failed: {resp.text}")
            
            print("   - Logging in...")
            resp = client.post("/auth/login", json={"email": email, "password": password})
            resp.raise_for_status()
            token = resp.json()["access_token"]
            print("   ✅ Login successful")
            
            print("   - Testing AI Summary (OpenRouter)...")
            text = "Vercel is a platform for frontend frameworks and static sites, built to integrate with your headless content, commerce, or database."
            
            resp = client.post(
                "/ai/summarize",
                json={"text": text},
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"   ✅ AI Summary Success: {data['summary']}")
            
        except httpx.HTTPStatusError as e:
            print(f"   ❌ API Error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_remote.py <YOUR_VERCEL_URL>")
        print("Example: python scripts/verify_remote.py https://moment-service.vercel.app")
        sys.exit(1)
        
    url = sys.argv[1]
    verify_deployment(url)
