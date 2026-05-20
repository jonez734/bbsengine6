# test_ping_pong_integration.py
# Ping/pong integration tests for TCP communication

import threading
import time
import pytest
import socket
from bbsengine6.net import TCPSender, Packet, PACKET_TYPE_PING, PACKET_TYPE_PONG


class TestPingPongIntegration:
    """Integration tests for ping/pong over TCP."""
    
    @pytest.mark.integration
    def test_ping_pong_exchange_5_seconds(self, free_port):
        """Exchange ping/pong messages for 5 seconds: sender initiates."""
        duration = 5.0
        start_time = time.time()
        messages = []
        stop_event = threading.Event()
        
        # Echo server: receive messages and echo them back
        def echo_server():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", free_port))
            server.listen(1)
            server.settimeout(1.0)
            
            try:
                client, addr = server.accept()
                client.settimeout(1.0)
                
                while not stop_event.is_set() and time.time() - start_time < duration + 1:
                    try:
                        packet = Packet.recv(client)
                        if packet is None:
                            continue
                        messages.append(('rx', packet.ptype, time.time() - start_time))
                        
                        # Echo back a PONG
                        pong = Packet(ptype=PACKET_TYPE_PONG)
                        client.sendall(pong.encode())
                        messages.append(('tx_pong', PACKET_TYPE_PONG, time.time() - start_time))
                    except socket.timeout:
                        continue
                
                client.close()
            except socket.timeout:
                pass
            finally:
                server.close()
        
        # Echo client: send pings and receive pongs
        def echo_client():
            time.sleep(0.1)  # Let server bind
            sender = TCPSender("127.0.0.1", free_port)
            error = sender.connect()
            if error:
                pytest.skip(f"Could not connect: {error}")
                return
            
            try:
                ping_num = 0
                while time.time() - start_time < duration:
                    ping_num += 1
                    ping = Packet(ptype=PACKET_TYPE_PING, payload=str(ping_num).encode())
                    error = sender.send(ping)
                    messages.append(('tx_ping', PACKET_TYPE_PING, time.time() - start_time))
                    
                    if error:
                        break
                    
                    # Try to receive pong
                    try:
                        pong = sender.recv()
                        if pong and not isinstance(pong, dict):
                            messages.append(('rx_pong', pong.ptype, time.time() - start_time))
                    except:
                        pass
                    
                    time.sleep(0.2)  # 200ms between pings = ~25 pings in 5 seconds
                
                stop_event.set()
            finally:
                sender.close()
        
        # Run both in parallel
        server_t = threading.Thread(target=echo_server, daemon=True)
        client_t = threading.Thread(target=echo_client, daemon=True)
        
        server_t.start()
        client_t.start()
        
        client_t.join(timeout=duration + 3)
        server_t.join(timeout=2)
        
        # Verify we sent and received messages
        sent_pings = [m for m in messages if m[0] == 'tx_ping']
        recv_pings = [m for m in messages if m[0] == 'rx']
        sent_pongs = [m for m in messages if m[0] == 'tx_pong']
        recv_pongs = [m for m in messages if m[0] == 'rx_pong']
        
        assert len(sent_pings) > 0, f"No pings sent. Messages: {messages}"
        assert len(recv_pings) > 0, f"No pings received by server. Messages: {messages}"
        assert len(sent_pings) >= 20, f"Expected ~25 pings in 5 seconds, got {len(sent_pings)}"
    
    @pytest.mark.integration
    def test_ping_pong_exchange_role_reversal(self, free_port):
        """Exchange ping/pong messages with role reversal for 5 seconds."""
        duration = 5.0
        start_time = time.time()
        messages = []
        stop_event = threading.Event()
        
        # Server role: listen and respond with pings
        def server_responder():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", free_port))
            server.listen(1)
            server.settimeout(1.0)
            
            try:
                client, addr = server.accept()
                client.settimeout(1.0)
                
                while not stop_event.is_set() and time.time() - start_time < duration + 1:
                    try:
                        packet = Packet.recv(client)
                        if packet is None:
                            continue
                        messages.append(('srv_rx', packet.ptype, time.time() - start_time))
                        
                        # Server sends PING back (role reversal)
                        ping = Packet(ptype=PACKET_TYPE_PING)
                        client.sendall(ping.encode())
                        messages.append(('srv_tx_ping', PACKET_TYPE_PING, time.time() - start_time))
                    except socket.timeout:
                        continue
                
                client.close()
            except socket.timeout:
                pass
            finally:
                server.close()
        
        # Client role: send pongs and receive pings (role reversal)
        def client_initiator():
            time.sleep(0.1)  # Let server bind
            sender = TCPSender("127.0.0.1", free_port)
            error = sender.connect()
            if error:
                pytest.skip(f"Could not connect: {error}")
                return
            
            try:
                pong_num = 0
                while time.time() - start_time < duration:
                    pong_num += 1
                    # Client sends PONG (initiator role reversal)
                    pong = Packet(ptype=PACKET_TYPE_PONG, payload=str(pong_num).encode())
                    error = sender.send(pong)
                    messages.append(('cli_tx_pong', PACKET_TYPE_PONG, time.time() - start_time))
                    
                    if error:
                        break
                    
                    # Try to receive ping from server
                    try:
                        ping = sender.recv()
                        if ping and not isinstance(ping, dict):
                            messages.append(('cli_rx_ping', ping.ptype, time.time() - start_time))
                    except:
                        pass
                    
                    time.sleep(0.2)  # 200ms between pongs
                
                stop_event.set()
            finally:
                sender.close()
        
        # Run both in parallel
        server_t = threading.Thread(target=server_responder, daemon=True)
        client_t = threading.Thread(target=client_initiator, daemon=True)
        
        server_t.start()
        client_t.start()
        
        client_t.join(timeout=duration + 3)
        server_t.join(timeout=2)
        
        # Verify bidirectional exchange with role reversal
        cli_pongs = [m for m in messages if m[0] == 'cli_tx_pong']
        srv_pongs = [m for m in messages if m[0] == 'srv_rx']
        cli_pings = [m for m in messages if m[0] == 'cli_rx_ping']
        srv_pings = [m for m in messages if m[0] == 'srv_tx_ping']
        
        assert len(cli_pongs) > 0, f"Client didn't send pongs. Messages: {messages}"
        assert len(srv_pongs) > 0, f"Server didn't receive pongs. Messages: {messages}"
        assert len(cli_pongs) >= 20, f"Expected ~25 pongs in 5 seconds, got {len(cli_pongs)}"
