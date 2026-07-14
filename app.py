#GHUMMMMMMM...A
#JOIN CHANNEL  https://t.me/bloodbrx98


from flask import Flask, request, jsonify
import json, os, aiohttp, asyncio, requests, binascii
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
import like_pb2, like_count_pb2, uid_generator_pb2
from google.protobuf.message import DecodeError
import itertools

app = Flask(__name__)

ACCOUNTS_FILE = 'accounts.json'
BATCH_SIZE = 23

# ✅ JWT API URLs (Both Railway APIs)
JWT_API_1 = "https://jwtlike.up.railway.app/semy"
JWT_API_2 = "https://jwtlike2.up.railway.app/semy"

# ✅ Load accounts
def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            data = json.load(f)
            # Handle both formats: list of objects OR list of lists
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    # Format: [{"uid": 123, "password": "xyz"}, ...]
                    return [(str(item.get('uid')), item.get('password')) for item in data if item.get('uid') and item.get('password')]
                elif isinstance(data[0], list):
                    # Format: [["uid", "password"], ...]
                    return [(str(item[0]), item[1]) for item in data if len(item) >= 2]
    return []

# ✅ Get account list as list of (uid, password)
def get_account_list():
    accounts = load_accounts()
    return list(accounts)

# ✅ Generate token from Railway API (handles {"jwt": "token"} format)
async def fetch_token_from_api(session, uid, password, api_url):
    url = f"{api_url}?uid={uid}&password={password}"
    try:
        async with session.get(url, timeout=10) as res:
            if res.status == 200:
                text = await res.text()
                try:
                    data = json.loads(text)
                    
                    # Handle Railway API format: {"jwt": "token", "success": true, ...}
                    if isinstance(data, dict) and "jwt" in data:
                        return data["jwt"]
                    
                    # Fallback for other formats if needed
                    elif isinstance(data, list) and len(data) > 0 and "token" in data[0]:
                        return data[0]["token"]
                    elif isinstance(data, dict) and "token" in data:
                        return data["token"]
                except:
                    return None
    except:
        return None
    return None

# ✅ Generate tokens for a batch (distribute between 2 Railway APIs)
async def generate_tokens_for_batch(batch_accounts):
    tokens = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        # Distribute accounts between two APIs
        mid = len(batch_accounts) // 2
        
        # First half - API 1 (jwtlike)
        for uid, password in batch_accounts[:mid]:
            tasks.append(fetch_token_from_api(session, uid, password, JWT_API_1))
        
        # Second half - API 2 (jwtlike2)
        for uid, password in batch_accounts[mid:]:
            tasks.append(fetch_token_from_api(session, uid, password, JWT_API_2))
        
        results = await asyncio.gather(*tasks)
        tokens = [token for token in results if token]
    
    return tokens

# ✅ Get next batch of accounts (circular with repeat from start)
def get_next_batch(account_list, start_index):
    if not account_list:
        return [], 0
    
    total_accounts = len(account_list)
    
    # If start_index exceeds list length, wrap around to 0
    if start_index >= total_accounts:
        start_index = 0
    
    # Get accounts from start_index
    batch = []
    
    # Case 1: Enough accounts from current position
    if start_index + BATCH_SIZE <= total_accounts:
        batch = account_list[start_index:start_index + BATCH_SIZE]
        next_start = start_index + BATCH_SIZE
    else:
        # Case 2: Not enough accounts from current position
        # Take remaining accounts from current position to end
        remaining_from_current = account_list[start_index:]
        batch.extend(remaining_from_current)
        
        # Calculate how many more needed to reach BATCH_SIZE
        needed = BATCH_SIZE - len(batch)
        
        # Take needed accounts from the beginning (circular)
        batch.extend(account_list[:needed])
        
        # Next start will be from the beginning after we've wrapped
        next_start = needed
    
    # If next_start equals total_accounts, reset to 0
    if next_start >= total_accounts:
        next_start = 0
    
    return batch, next_start

# ✅ Get tokens in batches with distribution
async def get_tokens_in_batches():
    account_list = get_account_list()
    if not account_list:
        return []
    
    # Start from beginning
    start_index = 0
    batch, next_start = get_next_batch(account_list, start_index)
    
    # Generate tokens for this batch
    tokens = await generate_tokens_for_batch(batch)
    
    # Store next start index for next request
    global NEXT_START_INDEX
    NEXT_START_INDEX = next_start
    
    return tokens

# ✅ Encryption functions
def encrypt_message(plaintext):
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return binascii.hexlify(cipher.encrypt(pad(plaintext, AES.block_size))).decode()

def create_uid_proto(uid):
    pb = uid_generator_pb2.uid_generator()
    pb.saturn_ = int(uid)
    pb.garena = 1
    return pb.SerializeToString()

def create_like_proto(uid):
    pb = like_pb2.like()
    pb.uid = int(uid)
    return pb.SerializeToString()

def decode_protobuf(binary):
    try:
        pb = like_count_pb2.Info()
        pb.ParseFromString(binary)
        return pb
    except DecodeError:
        return None

def make_request(enc_uid, token):
    url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB54"
    }
    try:
        res = requests.post(url, data=bytes.fromhex(enc_uid), headers=headers, verify=False)
        return decode_protobuf(res.content)
    except:
        return None

# ✅ Send like request
async def send_request(enc_uid, token):
    url = "https://client.ind.freefiremobile.com/LikeProfile"
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB54"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=bytes.fromhex(enc_uid), headers=headers, ssl=False) as r:
                return r.status
    except Exception as e:
        print(f"Error in send_request: {e}")
        return None

# ✅ Send likes with batch tokens
async def send_likes(uid, tokens):
    enc_uid = encrypt_message(create_like_proto(uid))
    tasks = [send_request(enc_uid, token) for token in tokens]
    return await asyncio.gather(*tasks)

# ✅ Global counter for batch rotation
NEXT_START_INDEX = 0

@app.route('/like', methods=['GET'])
def like_handler():
    global NEXT_START_INDEX
    
    uid = request.args.get("uid")
    if not uid:
        return jsonify({"error": "Missing UID"}), 400

    try:
        # Get account list
        account_list = get_account_list()
        if not account_list:
            return jsonify({"error": "No accounts found"}), 401
        
        # Log current state
        current_index = NEXT_START_INDEX
        total_accounts = len(account_list)
        
        # Get next batch of accounts (circular with repeat)
        batch, NEXT_START_INDEX = get_next_batch(account_list, NEXT_START_INDEX)
        
        # Check if we're repeating accounts from start
        repeat_count = 0
        if current_index + len(batch) > total_accounts:
            repeat_count = (current_index + len(batch)) - total_accounts
        
        # Generate tokens for this batch (distributed between 2 Railway APIs)
        tokens = asyncio.run(generate_tokens_for_batch(batch))
        
        if not tokens:
            return jsonify({"error": "No valid tokens generated"}), 401

        # Get player info before likes
        enc_uid = encrypt_message(create_uid_proto(uid))
        before = make_request(enc_uid, tokens[0])
        if not before:
            return jsonify({"error": "Failed to retrieve player info"}), 500

        before_data = json.loads(MessageToJson(before))
        likes_before = int(before_data.get("AccountInfo", {}).get("Likes", 0))
        nickname = before_data.get("AccountInfo", {}).get("PlayerNickname", "Unknown")

        # Send likes
        responses = asyncio.run(send_likes(uid, tokens))
        success_count = sum(1 for r in responses if r == 200)
        failed_count = len(tokens) - success_count

        # Get player info after likes
        after = make_request(enc_uid, tokens[0])
        likes_after = likes_before
        if after:
            after_data = json.loads(MessageToJson(after))
            likes_after = int(after_data.get("AccountInfo", {}).get("Likes", 0))

        # Prepare response data
        response_data = {
            "PlayerNickname": nickname,
            "UID": uid,
            "LikesBefore": likes_before,
            "LikesAfter": likes_after,
            "LikesGivenByAPI": likes_after - likes_before,
            "SuccessfulRequests": success_count,
            "FailedRequests": failed_count,
            "TotalRequests": len(tokens),
            "TokensGenerated": len(tokens),
            "BatchSize": len(batch),
            "CurrentStartIndex": current_index,
            "NextBatchStart": NEXT_START_INDEX,
            "TotalAccounts": total_accounts,
            "AccountsRepeatedFromStart": repeat_count,
            "BatchAccounts": [uid for uid, _ in batch[:10]] + (["..."] if len(batch) > 10 else []),
            "JWTAPIUsed": "Railway API 1 & Railway API 2",
            "APIs": [JWT_API_1, JWT_API_2],
            "status": 1 if likes_after > likes_before else 2,
            "developer": "semy"
        }
        
        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/')
def home():
    account_list = get_account_list()
    account_count = len(account_list)
    return jsonify({
        "status": "online", 
        "message": "Like API is running ✅",
        "total_accounts": account_count,
        "batch_size": BATCH_SIZE,
        "jwt_apis": [JWT_API_1, JWT_API_2],
        "response_format": '{"jwt": "token"}',
        "batch_rotation": "circular with repeat from start",
        "developer": "semy"
    })

# ✅ For local testing
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)