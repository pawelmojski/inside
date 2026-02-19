"""
Admin Console - Interactive SSH menu for administrators (Paramiko version)
Allows joining, watching, and managing active sessions
"""
import logging
import time
import socket
import select
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class AdminConsoleParamiko:
    """Interactive admin console accessible via direct SSH to gate (Paramiko version)"""
    
    def __init__(self, user_info: dict, tower_client, session_multiplexer_registry=None):
        self.user = user_info
        self.tower = tower_client
        self.multiplexer_registry = session_multiplexer_registry
        self.channel = None
        self.running = True
        
    def run(self, channel):
        """Main console loop"""
        self.channel = channel
        
        try:
            # Clear screen and show banner
            self.clear_screen()
            self.show_banner()
            
            while self.running:
                self.show_menu()
                choice = self.get_input("\nSelect option (1-9): ")
                
                if choice == '1':
                    self.show_active_stays()
                elif choice == '2':
                    self.show_active_sessions()
                elif choice == '3':
                    self.join_session()
                elif choice == '4':
                    self.watch_session()
                elif choice == '5':
                    self.kill_session()
                elif choice == '9':
                    self.write("\n\nGoodbye!\n")
                    self.running = False
                    break
                else:
                    self.write("\nInvalid option. Try again.\n")
                    time.sleep(1)
        except KeyboardInterrupt:
            self.write("\n\nDisconnected.\n")
        except Exception as e:
            logger.error(f"Admin console error: {e}", exc_info=True)
            self.write(f"\n\nError: {e}\n")
        finally:
            if not channel.closed:
                channel.close()
    
    def clear_screen(self):
        """Clear terminal screen"""
        self.write("\033[2J\033[H")
    
    def show_banner(self):
        """Display console banner"""
        banner = """
========================================
INSIDE - ADMIN CONSOLE
========================================

Connected as: {username} ({fullname})
Permission Level: {level}
Gate: {gate}
Time: {time}

""".format(
            username=self.user.get('username', 'unknown'),
            fullname=self.user.get('full_name', 'Unknown User'),
            level=self.user.get('permission_level', '?'),
            gate=socket.gethostname(),
            time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        self.write(banner)
    
    def show_menu(self):
        """Display main menu"""
        menu = """
========================================
MAIN MENU
========================================

1. Active Stays
2. Active Sessions
3. Join Session (read-write) - coming soon
4. Watch Session (read-only) - coming soon
5. Kill Session
6. Audit Logs - coming soon
7. Grant Debug - coming soon
8. MFA Status - coming soon
9. Exit

"""
        self.write(menu)
    
    def show_active_stays(self):
        """Display all active stays"""
        self.write("\n")
        self.write("=" * 60 + "\n")
        self.write("ACTIVE STAYS\n")
        self.write("=" * 60 + "\n\n")
        
        try:
            stays = self.tower.get_active_stays()
            
            if not stays:
                self.write("No active stays.\n\n")
                self.wait_for_key()
                return
            
            for stay in stays:
                stay_id = stay.get('id', '?')
                user_name = stay.get('user_name', 'Unknown')
                duration = self._format_duration(stay.get('duration', 0))
                sessions = stay.get('sessions', [])
                active_sessions = [s for s in sessions if s.get('is_active')]
                
                self.write(f"Stay #{stay_id} - {user_name}\n")
                self.write(f"  Duration: {duration}\n")
                self.write(f"  Sessions: {len(active_sessions)} active / {len(sessions)} total\n")
                
                # Show session details
                for sess in sessions[:5]:  # Show max 5 sessions per stay
                    status = "ACTIVE" if sess.get('is_active') else "CLOSED"
                    proto = sess.get('protocol', '?').upper()
                    backend_ip = sess.get('backend_ip', '?')
                    session_id = sess.get('session_id', '?')[:50]
                    
                    self.write(f"    [{status}] {proto} -> {backend_ip}\n")
                    self.write(f"      {session_id}\n")
                
                if len(sessions) > 5:
                    self.write(f"    ... and {len(sessions) - 5} more\n")
                
                self.write("\n")
            
            self.write("=" * 60 + "\n")
        except Exception as e:
            logger.error(f"Error fetching active stays: {e}", exc_info=True)
            self.write(f"\nError: {e}\n\n")
        
        self.wait_for_key()
    
    def show_active_sessions(self):
        """Display all active sessions"""
        self.write("\n")
        self.write("=" * 80 + "\n")
        self.write("ACTIVE SESSIONS\n")
        self.write("=" * 80 + "\n\n")
        
        try:
            sessions = self.tower.get_active_sessions()
            
            if not sessions:
                self.write("No active sessions.\n\n")
                self.wait_for_key()
                return
            
            for idx, sess in enumerate(sessions, 1):
                user_name = sess.get('user_name', 'Unknown')
                server_name = sess.get('server_name', '?')
                protocol = sess.get('protocol', '?').upper()
                duration = self._format_duration(sess.get('duration', 0))
                session_id = sess.get('session_id', '')
                backend_ip = sess.get('backend_ip', '?')
                ssh_user = sess.get('ssh_username', '?')
                source_ip = sess.get('source_ip', '?')
                
                self.write(f"[{idx}] {user_name} -> {server_name}\n")
                self.write(f"    Protocol: {protocol} | Duration: {duration}\n")
                self.write(f"    Backend: {backend_ip}:{sess.get('backend_port', 22)} (ssh: {ssh_user})\n")
                self.write(f"    Source: {source_ip}\n")
                self.write(f"    Session: {session_id}\n")
                self.write("\n")
            
            self.write("=" * 80 + "\n")
        except Exception as e:
            logger.error(f"Error fetching active sessions: {e}", exc_info=True)
            self.write(f"\nError: {e}\n\n")
        
        self.wait_for_key()
    
    def join_session(self):
        """Join an existing session (read-write)"""
        self.write("\n")
        self.write("=" * 60 + "\n")
        self.write("JOIN SESSION (Read-Write)\n")
        self.write("=" * 60 + "\n\n")
        
        if not self.multiplexer_registry:
            self.write("Session multiplexer not available on this gate.\n\n")
            self.wait_for_key()
            return
        
        try:
            # Get local sessions on this gate that can be joined
            sessions = self.tower.get_active_sessions()
            
            if not sessions:
                self.write("No active sessions available to join.\n\n")
                self.wait_for_key()
                return
            
            # Filter to only sessions on this gate with multiplexer
            joinable_sessions = []
            for sess in sessions:
                session_id = sess.get('session_id')
                if session_id and self.multiplexer_registry.get_session(session_id):
                    joinable_sessions.append(sess)
            
            if not joinable_sessions:
                self.write(f"No joinable sessions found on this gate.\n")
                self.write(f"Total active sessions: {len(sessions)}\n")
                self.write(f"Sessions with multiplexer: 0\n\n")
                self.write("Note: Only SSH sessions started after v2.0 can be joined.\n\n")
                self.wait_for_key()
                return
            
            # Display joinable sessions
            self.write(f"Found {len(joinable_sessions)} joinable session(s):\n\n")
            
            for idx, sess in enumerate(joinable_sessions, 1):
                user_name = sess.get('user_name', 'Unknown')
                server_name = sess.get('server_name', '?')
                duration = self._format_duration(sess.get('duration', 0))
                session_id = sess.get('session_id', '')[:50]
                
                self.write(f"[{idx}] {user_name} -> {server_name} ({duration})\n")
                self.write(f"    {session_id}\n")
            
            self.write("\n")
            
            # Get user choice
            choice = self.get_input("Enter session number to join (0 to cancel): ")
            
            if choice == '0':
                self.write("Cancelled.\n\n")
                self.wait_for_key()
                return
            
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(joinable_sessions):
                    self.write("Invalid session number.\n\n")
                    self.wait_for_key()
                    return
                
                selected_session = joinable_sessions[idx]
                session_id = selected_session.get('session_id')
                
                # Get multiplexer
                multiplexer = self.multiplexer_registry.get_session(session_id)
                if not multiplexer:
                    self.write("Session no longer available.\n\n")
                    self.wait_for_key()
                    return
                
                # Join the session
                self._attach_to_session(multiplexer, mode='join')
                
            except ValueError:
                self.write("Invalid input. Enter a number.\n\n")
                self.wait_for_key()
            
        except Exception as e:
            logger.error(f"Error joining session: {e}", exc_info=True)
            self.write(f"\nError: {e}\n\n")
            self.wait_for_key()
    
    def watch_session(self):
        """Watch an existing session (read-only)"""
        self.write("\n")
        self.write("=" * 60 + "\n")
        self.write("WATCH SESSION (Read-Only)\n")
        self.write("=" * 60 + "\n\n")
        
        if not self.multiplexer_registry:
            self.write("Session multiplexer not available on this gate.\n\n")
            self.wait_for_key()
            return
        
        try:
            # Get local sessions on this gate that can be watched
            sessions = self.tower.get_active_sessions()
            
            if not sessions:
                self.write("No active sessions available to watch.\n\n")
                self.wait_for_key()
                return
            
            # Filter to only sessions on this gate with multiplexer
            watchable_sessions = []
            for sess in sessions:
                session_id = sess.get('session_id')
                if session_id and self.multiplexer_registry.get_session(session_id):
                    watchable_sessions.append(sess)
            
            if not watchable_sessions:
                self.write(f"No watchable sessions found on this gate.\n")
                self.write(f"Total active sessions: {len(sessions)}\n")
                self.write(f"Sessions with multiplexer: 0\n\n")
                self.write("Note: Only SSH sessions started after v2.0 can be watched.\n\n")
                self.wait_for_key()
                return
            
            # Display watchable sessions
            self.write(f"Found {len(watchable_sessions)} watchable session(s):\n\n")
            
            for idx, sess in enumerate(watchable_sessions, 1):
                user_name = sess.get('user_name', 'Unknown')
                server_name = sess.get('server_name', '?')
                duration = self._format_duration(sess.get('duration', 0))
                session_id = sess.get('session_id', '')[:50]
                
                self.write(f"[{idx}] {user_name} -> {server_name} ({duration})\n")
                self.write(f"    {session_id}\n")
            
            self.write("\n")
            
            # Get user choice
            choice = self.get_input("Enter session number to watch (0 to cancel): ")
            
            if choice == '0':
                self.write("Cancelled.\n\n")
                self.wait_for_key()
                return
            
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(watchable_sessions):
                    self.write("Invalid session number.\n\n")
                    self.wait_for_key()
                    return
                
                selected_session = watchable_sessions[idx]
                session_id = selected_session.get('session_id')
                
                # Get multiplexer
                multiplexer = self.multiplexer_registry.get_session(session_id)
                if not multiplexer:
                    self.write("Session no longer available.\n\n")
                    self.wait_for_key()
                    return
                
                # Watch the session
                self._attach_to_session(multiplexer, mode='watch')
                
            except ValueError:
                self.write("Invalid input. Enter a number.\n\n")
                self.wait_for_key()
            
        except Exception as e:
            logger.error(f"Error watching session: {e}", exc_info=True)
            self.write(f"\nError: {e}\n\n")
            self.wait_for_key()
    
    def kill_session(self):
        """Terminate an active session"""
        self.write("\n")
        self.write("=" * 60 + "\n")
        self.write("KILL SESSION\n")
        self.write("=" * 60 + "\n\n")
        
        try:
            # Get active sessions
            sessions = self.tower.get_active_sessions()
            
            if not sessions:
                self.write("No active sessions to kill.\n\n")
                self.wait_for_key()
                return
            
            # Display sessions with numbers
            for idx, sess in enumerate(sessions, 1):
                user_name = sess.get('user_name', 'Unknown')
                server_name = sess.get('server_name', '?')
                session_id = sess.get('session_id', '')[:50]
                backend_ip = sess.get('backend_ip', '?')
                
                self.write(f"[{idx}] {user_name} -> {server_name} ({backend_ip})\n")
                self.write(f"    {session_id}\n")
            
            self.write("\n")
            
            # Get user choice
            choice = self.get_input("Enter session number to kill (0 to cancel): ")
            
            if choice == '0':
                self.write("Cancelled.\n\n")
                self.wait_for_key()
                return
            
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(sessions):
                    self.write(f"Invalid session number.\n\n")
                    self.wait_for_key()
                    return
                
                selected_session = sessions[idx]
                session_id = selected_session.get('session_id')
                
                # Confirm
                confirm = self.get_input(f"\nKill session {session_id[:50]}? (yes/no): ")
                if confirm.lower() != 'yes':
                    self.write("Cancelled.\n\n")
                    self.wait_for_key()
                    return
                
                # Kill session via API
                result = self.tower.kill_session(session_id)
                
                if result.get('success'):
                    self.write(f"\nSession killed successfully.\n\n")
                else:
                    error = result.get('error', 'Unknown error')
                    self.write(f"\nFailed to kill session: {error}\n\n")
                
            except ValueError:
                self.write(f"Invalid input. Enter a number.\n\n")
            
        except Exception as e:
            logger.error(f"Error killing session: {e}", exc_info=True)
            self.write(f"\nError: {e}\n\n")
        
        self.wait_for_key()
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def get_input(self, prompt: str) -> str:
        """Get input from user"""
        self.write(prompt)
        
        # Read input character by character until newline
        input_buffer = ""
        while True:
            try:
                char = self.channel.recv(1)
                if not char:
                    return ""
                
                char = char.decode('utf-8', errors='ignore')
                
                # Handle newline
                if char in ['\r', '\n']:
                    self.write("\n")
                    return input_buffer.strip()
                
                # Handle backspace
                elif char in ['\x7f', '\x08']:
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        # Move cursor back, overwrite with space, move back again
                        self.write("\x08 \x08")
                    continue
                
                # Handle Ctrl+C
                elif char == '\x03':
                    raise KeyboardInterrupt()
                
                # Normal character
                elif char.isprintable():
                    input_buffer += char
                    self.write(char)  # Echo character
                
            except Exception as e:
                logger.error(f"Error reading input: {e}")
                return ""
    
    def write(self, text: str):
        """Write text to channel"""
        try:
            if self.channel and not self.channel.closed:
                # Replace \n with \r\n for proper terminal line breaks
                text = text.replace('\n', '\r\n')
                self.channel.send(text.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error writing to channel: {e}")
    
    def _attach_to_session(self, multiplexer, mode='watch'):
        """Attach to a multiplexed session (watch or join mode)
        
        Args:
            multiplexer: SessionMultiplexer instance
            mode: 'watch' (read-only) or 'join' (read-write)
        """
        import uuid
        
        watcher_id = f"admin_{self.user['username']}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Add this channel as watcher/participant
            success = multiplexer.add_watcher(
                watcher_id=watcher_id,
                channel=self.channel,
                username=self.user['username'],
                mode=mode
            )
            
            if not success:
                self.write("\nFailed to attach to session.\n\n")
                return
            
            # Enter live streaming mode
            mode_text = "WATCH MODE (Read-Only)" if mode == 'watch' else "JOIN MODE (Read-Write)"
            self.write(f"\n{mode_text}\n")
            self.write("Press Ctrl+D or Ctrl+C to detach\n\n")
            
            # Stream loop
            try:
                while not self.channel.closed:
                    # Check for input from admin (only if join mode)
                    r, w, x = select.select([self.channel], [], [], 0.1)
                    
                    if self.channel in r:
                        try:
                            data = self.channel.recv(1024)
                            if not data:
                                break
                            
                            # Handle Ctrl+D (EOF) or Ctrl+C
                            if b'\x04' in data or b'\x03' in data:
                                self.write("\n\nDetaching from session...\n")
                                break
                            
                            # If join mode, forward input to backend via multiplexer
                            if mode == 'join':
                                multiplexer.handle_participant_input(watcher_id, data)
                        
                        except socket.timeout:
                            continue
                        except Exception as e:
                            logger.error(f"Error reading admin input: {e}")
                            break
                    
                    # Output is automatically sent by multiplexer.broadcast_output()
                    # which was called in forward_channel()
            
            except KeyboardInterrupt:
                self.write("\n\nDetaching from session...\n")
            
        finally:
            # Remove watcher
            multiplexer.remove_watcher(watcher_id)
            self.write("\nReturning to main menu...\n\n")
            time.sleep(1)
    
    def wait_for_key(self):
        """Wait for user to press any key"""
        self.get_input("Press Enter to continue...")
