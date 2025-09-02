#!/usr/bin/env python3

"""
Analyze KİK v2 hash generation by examining JavaScript code patterns
and trying to reverse engineer the hash generation logic.
"""

import asyncio
import json
import hashlib
import hmac
import base64
from fastmcp import Client
from mcp_server_main import app

def analyze_webpack_hash_patterns():
    """
    Analyze the webpack JavaScript code you provided to find hash generation patterns
    """
    print("🔍 Analyzing webpack hash generation patterns...")
    
    # From the JavaScript code, I can see several hash/ID generation patterns:
    hash_patterns = {
        # Webpack chunk system hashes (from the JS code)
        "webpack_chunks": {
            315: "d9a9486a4f5ba326",
            531: "cd8fb385c88033ae", 
            671: "04c48b287646627a",
            856: "682c9a7b87351f90",
            1017: "9de022378fc275f6",
            # ... many more from the __webpack_require__.u function
        },
        
        # Symbol generation from Zone.js
        "zone_symbols": [
            "__zone_symbol__",
            "__Zone_symbol_prefix",
            "Zone.__symbol__"
        ],
        
        # Angular module federation patterns
        "module_federation": [
            "__webpack_modules__",
            "__webpack_module_cache__",
            "__webpack_require__"
        ]
    }
    
    # The target hash format
    target_hash = "42f9bcd59e0dfbca36dec9accf5686c7a92aa97724cd8fc3550beb84b80409da"
    print(f"🎯 Target hash: {target_hash}")
    print(f"   Length: {len(target_hash)} characters")
    print(f"   Format: {'SHA256' if len(target_hash) == 64 else 'Other'} (64 chars = SHA256)")
    
    return hash_patterns

def test_webpack_style_hashing(data_dict):
    """Test webpack-style hash generation methods"""
    hashes = {}
    
    for key, value in data_dict.items():
        test_string = str(value)
        
        # Try various webpack-style hash methods
        hashes[f"webpack_md5_{key}"] = hashlib.md5(test_string.encode()).hexdigest()
        hashes[f"webpack_sha1_{key}"] = hashlib.sha1(test_string.encode()).hexdigest()  
        hashes[f"webpack_sha256_{key}"] = hashlib.sha256(test_string.encode()).hexdigest()
        
        # Try with various prefixes/suffixes (common in webpack)
        prefixed = f"__webpack__{test_string}"
        hashes[f"webpack_prefixed_sha256_{key}"] = hashlib.sha256(prefixed.encode()).hexdigest()
        
        # Try with module federation style
        module_style = f"shell:{test_string}"
        hashes[f"module_fed_sha256_{key}"] = hashlib.sha256(module_style.encode()).hexdigest()
        
        # Try JSON stringified
        json_style = json.dumps({"id": value, "type": "decision"}, separators=(',', ':'))
        hashes[f"json_sha256_{key}"] = hashlib.sha256(json_style.encode()).hexdigest()
        
        # Try with timestamp or sequence
        with_seq = f"{test_string}_0"
        hashes[f"seq_sha256_{key}"] = hashlib.sha256(with_seq.encode()).hexdigest()
        
    return hashes

def test_angular_routing_hashes(data_dict):
    """Test Angular routing/state management hash generation"""
    hashes = {}
    
    for key, value in data_dict.items():
        # Angular often uses route parameters for hash generation
        route_style = f"/kurul-kararlari/{value}"
        hashes[f"route_sha256_{key}"] = hashlib.sha256(route_style.encode()).hexdigest()
        
        # Component state style
        state_style = f"KurulKararGoster_{value}"
        hashes[f"state_sha256_{key}"] = hashlib.sha256(state_style.encode()).hexdigest()
        
        # Angular module style
        module_style = f"kik.kurul.karar.{value}"
        hashes[f"module_sha256_{key}"] = hashlib.sha256(module_style.encode()).hexdigest()
        
    return hashes

def test_base64_encoding_variants(data_dict):
    """Test various base64 and encoding variants"""
    hashes = {}
    
    for key, value in data_dict.items():
        test_string = str(value)
        
        # Try base64 encoding then hashing
        b64_encoded = base64.b64encode(test_string.encode()).decode()
        hashes[f"b64_sha256_{key}"] = hashlib.sha256(b64_encoded.encode()).hexdigest()
        
        # Try URL-safe base64
        b64_url = base64.urlsafe_b64encode(test_string.encode()).decode()
        hashes[f"b64url_sha256_{key}"] = hashlib.sha256(b64_url.encode()).hexdigest()
        
        # Try hex encoding
        hex_encoded = test_string.encode().hex()
        hashes[f"hex_sha256_{key}"] = hashlib.sha256(hex_encoded.encode()).hexdigest()
        
    return hashes

async def test_hash_generation_comprehensive():
    print("🔐 Comprehensive KİK document hash generation analysis...")
    print("=" * 70)
    
    # First analyze the webpack patterns
    webpack_patterns = analyze_webpack_hash_patterns()
    
    client = Client(app)
    
    async with client:
        print("✅ MCP client connected")
        
        # Get sample decisions 
        print("\n📊 Getting sample decisions for hash analysis...")
        search_result = await client.call_tool("search_kik_v2_decisions", {
            "decision_type": "uyusmazlik",
            "karar_metni": "2024"
        })
        
        if hasattr(search_result, 'content') and search_result.content:
            search_data = json.loads(search_result.content[0].text)
            decisions = search_data.get('decisions', [])
            
            if decisions:
                print(f"✅ Found {len(decisions)} decisions")
                
                # Test with first decision
                sample_decision = decisions[0]
                print(f"\n📋 Sample decision for hash analysis:")
                for key, value in sample_decision.items():
                    print(f"   {key}: {value}")
                
                target_hash = "42f9bcd59e0dfbca36dec9accf5686c7a92aa97724cd8fc3550beb84b80409da"
                print(f"\n🎯 Target hash to match: {target_hash}")
                
                all_hashes = {}
                
                # Test different hash generation methods
                print(f"\n🔨 Testing webpack-style hashing...")
                webpack_hashes = test_webpack_style_hashing(sample_decision)
                all_hashes.update(webpack_hashes)
                
                print(f"🔨 Testing Angular routing hashes...")  
                angular_hashes = test_angular_routing_hashes(sample_decision)
                all_hashes.update(angular_hashes)
                
                print(f"🔨 Testing base64 encoding variants...")
                b64_hashes = test_base64_encoding_variants(sample_decision)
                all_hashes.update(b64_hashes)
                
                # Check for matches
                print(f"\n🎯 Checking for hash matches...")
                matches_found = []
                partial_matches = []
                
                for hash_name, hash_value in all_hashes.items():
                    if hash_value == target_hash:
                        matches_found.append((hash_name, hash_value))
                        print(f"   🎉 EXACT MATCH FOUND: {hash_name}")
                    elif hash_value[:8] == target_hash[:8]:  # First 8 chars match
                        partial_matches.append((hash_name, hash_value))
                        print(f"   🔍 Partial match (first 8): {hash_name} -> {hash_value[:16]}...")
                    elif hash_value[-8:] == target_hash[-8:]:  # Last 8 chars match
                        partial_matches.append((hash_name, hash_value))
                        print(f"   🔍 Partial match (last 8): {hash_name} -> ...{hash_value[-16:]}")
                
                if not matches_found and not partial_matches:
                    print(f"   ❌ No matches found")
                    print(f"\n📝 Sample generated hashes (first 10):")
                    for i, (hash_name, hash_value) in enumerate(list(all_hashes.items())[:10]):
                        print(f"   {hash_name}: {hash_value}")
                
                # Try combinations with other decisions
                print(f"\n🔄 Testing hash combinations with multiple decisions...")
                if len(decisions) > 1:
                    for i, decision in enumerate(decisions[1:3]):  # Test 2 more
                        print(f"\n   Testing decision {i+2}: {decision.get('kararNo')}")
                        decision_hashes = test_webpack_style_hashing(decision)
                        
                        for hash_name, hash_value in decision_hashes.items():
                            if hash_value == target_hash:
                                print(f"   🎉 MATCH FOUND in decision {i+2}: {hash_name}")
                                matches_found.append((f"decision_{i+2}_{hash_name}", hash_value))
                
                # Try composite hashes (combining multiple fields)
                print(f"\n🔗 Testing composite hash generation...")
                composite_tests = [
                    f"{sample_decision.get('gundemMaddesiId')}_{sample_decision.get('kararNo')}",
                    f"{sample_decision.get('kararNo')}_{sample_decision.get('kararTarihi')}",
                    f"uyusmazlik_{sample_decision.get('gundemMaddesiId')}_{sample_decision.get('kararTarihi')}",
                    json.dumps(sample_decision, separators=(',', ':'), sort_keys=True),
                    f"{sample_decision.get('basvuran')}_{sample_decision.get('gundemMaddesiId')}",
                ]
                
                for i, composite_str in enumerate(composite_tests):
                    composite_hash = hashlib.sha256(composite_str.encode()).hexdigest()
                    if composite_hash == target_hash:
                        print(f"   🎉 COMPOSITE MATCH FOUND: test_{i} -> {composite_str[:50]}...")
                        matches_found.append((f"composite_{i}", composite_hash))
                        
                print(f"\n🎯 Hash analysis completed!")
                print(f"   Total matches found: {len(matches_found)}")
                print(f"   Partial matches: {len(partial_matches)}")
                
            else:
                print("❌ No decisions found")
        else:
            print("❌ Search failed")
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_hash_generation_comprehensive())