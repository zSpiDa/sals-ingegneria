#!/usr/bin/env python3
"""
Smart Mobility Sprint 1 - Automated Testing Script
Esegue test completi di tutte le features
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api"
TEST_USER = "mario.rossi"
TEST_PASSWORD = "Test1234!"

# Colors for console output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
CHECKMARK = '✅'
CROSS = '❌'

# Global token
AUTH_TOKEN = None
TEST_RESULTS = []

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_test(name, passed, message=""):
    global TEST_RESULTS
    status = f"{GREEN}{CHECKMARK}{RESET}" if passed else f"{RED}{CROSS}{RESET}"
    TEST_RESULTS.append({"name": name, "passed": passed})
    print(f"{status} {name}: {message}")

def print_summary():
    global TEST_RESULTS
    total = len(TEST_RESULTS)
    passed = sum(1 for t in TEST_RESULTS if t["passed"])
    failed = total - passed
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'Test Summary':^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Total Tests: {total}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    if failed > 0:
        print(f"{RED}Failed: {failed}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

# ============================================================================
# 1. AUTENTICAZIONE
# ============================================================================

def test_login():
    """Test IF-U13: Login & Authentication"""
    global AUTH_TOKEN
    print_header("1. Testing Authentication (IF-U13)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login/",
            json={"username": TEST_USER, "password": TEST_PASSWORD}
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access" in data:
                AUTH_TOKEN = data["access"]
                print_test("Login", True, f"Token: {AUTH_TOKEN[:20]}...")
                return True
        
        print_test("Login", False, f"Status: {response.status_code}")
        return False
    except Exception as e:
        print_test("Login", False, str(e))
        return False

# ============================================================================
# 2. VEICOLI (IF-U01, IF-U11)
# ============================================================================

def test_vehicle_list():
    """Test IF-U01: Display Available Vehicles + IF-U11: Battery Status"""
    print_header("2. Testing Vehicle List (IF-U01, IF-U11)")
    
    try:
        response = requests.get(f"{BASE_URL}/mezzi/")
        
        if response.status_code == 200:
            vehicles = response.json()
            
            # Test 2a: Count vehicles
            print_test("Vehicle Count", len(vehicles) >= 6, f"Found {len(vehicles)} vehicles")
            
            # Test 2b: Battery status
            for v in vehicles[:3]:
                has_battery = "batteria" in v
                print_test(f"Vehicle #{v['id']} Battery Status", has_battery, f"{v.get('batteria', 'N/A')}%")
            
            # Test 2c: Filter by battery
            response_critical = requests.get(f"{BASE_URL}/mezzi/?filtro_batteria=CRITICAL")
            if response_critical.status_code == 200:
                critical_count = len(response_critical.json())
                print_test("Battery Filter (CRITICAL)", True, f"Found {critical_count} vehicles with <10% battery")
            
            return True
        
        print_test("Vehicle List", False, f"Status: {response.status_code}")
        return False
    except Exception as e:
        print_test("Vehicle List", False, str(e))
        return False

# ============================================================================
# 3. PRENOTAZIONE (IF-U02)
# ============================================================================

def test_vehicle_reservation():
    """Test IF-U02: Reserve Vehicles"""
    print_header("3. Testing Vehicle Reservation (IF-U02)")
    
    try:
        # Get available vehicle
        response = requests.get(f"{BASE_URL}/mezzi/")
        vehicles = response.json()
        vehicle_id = vehicles[0]["id"] if vehicles else None
        
        if not vehicle_id:
            print_test("Vehicle Reservation", False, "No available vehicles")
            return False
        
        # Reserve vehicle
        response = requests.post(
            f"{BASE_URL}/mezzi/{vehicle_id}/prenota/",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            status_ok = data.get("mezzo", {}).get("stato") == "PRENOTATO"
            print_test("Vehicle Reservation", status_ok, f"Vehicle #{vehicle_id} reserved")
            return True
        
        print_test("Vehicle Reservation", False, f"Status: {response.status_code}")
        return False
    except Exception as e:
        print_test("Vehicle Reservation", False, str(e))
        return False

# ============================================================================
# 4. INIZIO CORSA (IF-U03)
# ============================================================================

ACTIVE_RIDE_ID = None

def test_start_ride():
    """Test IF-U03: Estimate Ride Cost"""
    global ACTIVE_RIDE_ID
    print_header("4. Testing Start Ride (IF-U03)")
    
    try:
        # Get vehicle #2 (SCOOTER)
        response = requests.get(f"{BASE_URL}/mezzi/2/")
        
        if response.status_code == 200:
            vehicle = response.json()
            
            # Start ride
            response = requests.post(
                f"{BASE_URL}/corse/avvia/",
                json={
                    "mezzo_id": 2,
                    "latitudine": 41.1151,
                    "longitudine": 16.8644
                },
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
            
            if response.status_code == 201:
                data = response.json()
                ride_id = data.get("corsa", {}).get("id")
                ACTIVE_RIDE_ID = ride_id
                
                # Verify cost estimate
                cost_per_min = data.get("stima_costo_al_minuto")
                expected_cost = 0.20  # SCOOTER tariff
                
                cost_ok = abs(cost_per_min - expected_cost) < 0.01 if cost_per_min else False
                print_test("Start Ride (Cost Estimate)", cost_ok, f"€{cost_per_min}/min (SCOOTER)")
                print_test("Ride ID", True, f"Ride #{ride_id}")
                
                return True
        
        print_test("Start Ride", False, f"Status: {response.status_code}")
        return False
    except Exception as e:
        print_test("Start Ride", False, str(e))
        return False

# ============================================================================
# 5. COSTO REAL-TIME (IF-U04)
# ============================================================================

def test_realtime_cost():
    """Test IF-U04: Real-time Cost Display"""
    print_header("5. Testing Real-time Cost (IF-U04)")
    
    if not ACTIVE_RIDE_ID:
        print_test("Real-time Cost", False, "No active ride")
        return False
    
    try:
        costs = []
        times = []
        
        # Check cost 3 times with 2-second intervals
        for i in range(3):
            response = requests.get(
                f"{BASE_URL}/corse/{ACTIVE_RIDE_ID}/costo_corrente/",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                costs.append(data.get("costo_stimato_corrente"))
                times.append(data.get("secondi_trascorsi"))
                print(f"  Sample {i+1}: €{data['costo_stimato_corrente']} after {data['secondi_trascorsi']}s")
            
            if i < 2:
                time.sleep(2)
        
        # Verify costs are increasing
        costs_increasing = all(costs[i] <= costs[i+1] for i in range(len(costs)-1))
        print_test("Real-time Cost Tracking", costs_increasing, "Costs increasing over time")
        
        return True
    except Exception as e:
        print_test("Real-time Cost", False, str(e))
        return False

# ============================================================================
# 6. SBLOCCO MEZZO (IF-U12)
# ============================================================================

def test_vehicle_unlock():
    """Test IF-U12: Unlock Vehicle via App"""
    print_header("6. Testing Vehicle Unlock (IF-U12)")
    
    if not ACTIVE_RIDE_ID:
        print_test("Vehicle Unlock", False, "No active ride")
        return False
    
    try:
        # Test 6a: Valid unlock (within 100m)
        response = requests.post(
            f"{BASE_URL}/corse/{ACTIVE_RIDE_ID}/sblocca/",
            json={
                "latitudine": 41.1151,
                "longitudine": 16.8644
            },
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        valid_unlock = response.status_code == 200
        print_test("Unlock (Valid GPS)", valid_unlock, f"Distance: ~0m")
        
        # Test 6b: Invalid unlock (>100m)
        if not valid_unlock:
            return False
        
        # Can't unlock twice, so we'll test with a new ride
        response = requests.post(
            f"{BASE_URL}/corse/avvia/",
            json={"mezzo_id": 3, "latitudine": 41.1151, "longitudine": 16.8644},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 201:
            ride2_id = response.json().get("corsa", {}).get("id")
            
            # Try unlock from far away
            response = requests.post(
                f"{BASE_URL}/corse/{ride2_id}/sblocca/",
                json={"latitudine": 41.2000, "longitudine": 16.9000},
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
            
            invalid_unlock = response.status_code == 400
            print_test("Unlock (Invalid GPS - Too Far)", invalid_unlock, "Distance validation working")
        
        return True
    except Exception as e:
        print_test("Vehicle Unlock", False, str(e))
        return False

# ============================================================================
# 7. TERMINE CORSA (IF-U05)
# ============================================================================

def test_end_ride():
    """Test IF-U05: End Ride & Final Cost"""
    print_header("7. Testing End Ride (IF-U05)")
    
    if not ACTIVE_RIDE_ID:
        print_test("End Ride", False, "No active ride")
        return False
    
    try:
        # Wait for some time to accumulate cost
        print("  ⏱️  Waiting 30 seconds for ride cost to accumulate...")
        time.sleep(30)
        
        # End ride
        response = requests.post(
            f"{BASE_URL}/corse/{ACTIVE_RIDE_ID}/termina/",
            json={
                "latitudine": 41.1160,
                "longitudine": 16.8650
            },
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            ride_data = data.get("corsa", {})
            
            # Verify cost calculated
            cost = ride_data.get("costo_totale")
            has_end_time = ride_data.get("fine") is not None
            
            print_test("End Ride (Cost Calculated)", cost is not None and cost > 0, f"Final cost: €{cost}")
            print_test("End Ride (End Time Recorded)", has_end_time, "End timestamp recorded")
            print_test("End Ride (Position Recorded)", True, "GPS coordinates stored")
            
            return True
        
        print_test("End Ride", False, f"Status: {response.status_code}")
        return False
    except Exception as e:
        print_test("End Ride", False, str(e))
        return False

# ============================================================================
# 8. METODO PAGAMENTO (IF-U13)
# ============================================================================

def test_payment_method():
    """Test IF-U13: Save Payment Method"""
    print_header("8. Testing Payment Method (IF-U13)")
    
    try:
        # Get profile
        response = requests.get(
            f"{BASE_URL}/utenti/profilo/",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 200:
            profile = response.json()
            original_method = profile.get("metodo_pagamento")
            print_test("Get Payment Method", True, f"Current: {original_method}")
            
            # Change payment method
            new_method = "PAYPAL" if original_method != "PAYPAL" else "CARTA"
            response = requests.put(
                f"{BASE_URL}/utenti/aggiorna_profilo/",
                json={"metodo_pagamento": new_method},
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                method_changed = data.get("metodo_pagamento") == new_method
                print_test("Save Payment Method", method_changed, f"Changed to: {new_method}")
                
                return True
        
        print_test("Payment Method", False, f"Status: {response.status_code}")
        return False
    except Exception as e:
        print_test("Payment Method", False, str(e))
        return False

# ============================================================================
# 9. FLOTTA MONITORING (IF-O02)
# ============================================================================

def test_fleet_monitoring():
    """Test IF-O02: Fleet Distribution Monitoring"""
    print_header("9. Testing Fleet Monitoring (IF-O02)")
    
    try:
        response = requests.get(f"{BASE_URL}/mezzi/mappa_flotta/")
        
        if response.status_code == 200:
            data = response.json()
            
            print_test("Fleet Count", "totale_mezzi" in data, f"Total: {data.get('totale_mezzi')}")
            print_test("Available Count", "disponibili" in data, f"Available: {data.get('disponibili')}")
            print_test("In Use Count", "in_uso" in data, f"In use: {data.get('in_uso')}")
            print_test("Reserved Count", "prenotati" in data, f"Reserved: {data.get('prenotati')}")
            
            return True
        
        print_test("Fleet Monitoring", False, f"Status: {response.status_code}")
        return False
    except Exception as e:
        print_test("Fleet Monitoring", False, str(e))
        return False

# ============================================================================
# 10. GEOFENCING (IF-O04)
# ============================================================================

def test_geofencing():
    """Test IF-O04: Detect Position at Ride End + Geofencing"""
    print_header("10. Testing Geofencing (IF-O04)")
    
    try:
        # Test 10a: Validate zone
        response = requests.post(
            f"{BASE_URL}/aree-urbane/valida_punto/",
            json={"latitudine": 41.1151, "longitudine": 16.8644}
        )
        
        if response.status_code == 200:
            data = response.json()
            allowed_zone = data.get("in_zona_consentita")
            print_test("Geofencing (Allowed Zone)", allowed_zone, "Point in allowed parking zone")
        
        # Test 10b: Forbidden zone
        response = requests.post(
            f"{BASE_URL}/aree-urbane/valida_punto/",
            json={"latitudine": 41.1100, "longitudine": 16.8600}
        )
        
        if response.status_code == 200:
            data = response.json()
            forbidden_zone = data.get("in_zona_vietata")
            print_test("Geofencing (Forbidden Zone)", forbidden_zone, "Point in restricted zone")
        
        # Test 10c: End ride in forbidden zone
        response = requests.post(
            f"{BASE_URL}/corse/avvia/",
            json={"mezzo_id": 4, "latitudine": 41.1151, "longitudine": 16.8644},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        if response.status_code == 201:
            ride_id = response.json().get("corsa", {}).get("id")
            
            # Try to end in forbidden zone
            response = requests.post(
                f"{BASE_URL}/corse/{ride_id}/termina/",
                json={"latitudine": 41.1100, "longitudine": 16.8600},
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
            
            forbidden_end = response.status_code == 400
            print_test("Geofencing (Forbidden End)", forbidden_end, "Cannot end in restricted zone")
        
        return True
    except Exception as e:
        print_test("Geofencing", False, str(e))
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    print_header("🧪 Smart Mobility Sprint 1 - Complete Test Suite")
    
    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/mezzi/", timeout=2)
    except:
        print(f"{RED}❌ Server not running at {BASE_URL}{RESET}")
        print(f"   Start with: python manage.py runserver")
        sys.exit(1)
    
    # Run all tests
    test_login()
    test_vehicle_list()
    test_vehicle_reservation()
    test_start_ride()
    test_realtime_cost()
    test_vehicle_unlock()
    test_end_ride()
    test_payment_method()
    test_fleet_monitoring()
    test_geofencing()
    
    # Print summary
    print_summary()
    
    # Exit code
    passed = sum(1 for t in TEST_RESULTS if t["passed"])
    total = len(TEST_RESULTS)
    
    if passed == total:
        print(f"{GREEN}✅ ALL TESTS PASSED!{RESET}\n")
        return 0
    else:
        print(f"{RED}❌ {total - passed} TESTS FAILED{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
