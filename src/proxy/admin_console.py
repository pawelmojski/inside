"""
Admin Console - Interactive SSH menu for administrators
Allows joining, watching, and managing active sessions
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class AdminConsole:
    """Interactive admin console accessible via direct SSH to gate"""
    
    def __init__(self, user_info: dict, tower_client, session_manager):
        self.user = user_info
        self.tower = tower_client
        self.session_manager = session_manager
        self.channel = None
        self.running = True
        
    async def run(self, channel):
        """Main console loop"""
        self.channel = channel
        
        # Clear screen and show banner
        await self.clear_screen()
        await self.show_banner()
        
        while self.running:
            await self.show_menu()
            choice = await self.get_input("\nSelect option (1-9): ")
            
            if choice == '1':
                await self.show_active_stays()
            elif choice == '2':
                await self.show_active_sessions()
            elif choice == '3':
                await self.join_session()
            elif choice == '4':
                await self.watch_session()
            elif choice == '5':
                await self.kill_session()
            elif choice == '9':
                await self.write("\n\nGoodbye!\n")
                self.running = False
                break
            else:
                await self.write("\n⚠️  Invalid option. Try again.\n")
                await asyncio.sleep(1)
        
        channel.close()
    
    async def clear_screen(self):
        """Clear terminal screen"""
        await self.write("\033[2J\033[H")
    
    async def show_banner(self):
        """Display console banner"""
        banner = """
╔═════════════════════════════════════════════════╗
║             INSIDE — ADMIN CONSOLE              ║
╚═════════════════════════════════════════════════╝

  Connected as: {username}
  Permission Level: {level}
  Gate: {gate}
  Time: {time}

""".format(
            username=self.user.get('username', 'unknown'),
            level=self.user.get('permission_level', '?'),
            gate='gate-localhost',  # TODO: Get from config
            time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        await self.write(banner)
    
    async def show_menu(self):
        """Display main menu"""
        menu = """
┌─────────────────────────────────────────────────┐
│                   MAIN MENU                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. 👥 Active Stays                             │
│  2. 🔌 Active Sessions                          │
│  3. 🔗 Join Existing Session (read-write)       │
│  4. 👁️  Watch-only Session (read-only)          │
│  5. ⚠️  Kill Session                             │
│  6. 📋 Audit Logs (coming soon)                 │
│  7. 🔍 Grant Debug (coming soon)                │
│  8. 🔐 MFA Status (coming soon)                 │
│  9. 🚪 Exit                                      │
│                                                 │
└─────────────────────────────────────────────────┘
"""
        await self.write(menu)
    
    async def show_active_stays(self):
        """Show list of active stays"""
        await self.clear_screen()
        await self.write("\n╔═══════════════════════════════════════════════════════════════════╗\n")
        await self.write("║                        ACTIVE STAYS                               ║\n")
        await self.write("╚═══════════════════════════════════════════════════════════════════╝\n\n")
        
        try:
            # Fetch active stays from Tower API
            stays = await asyncio.to_thread(self.tower.get_active_stays)
            
            if not stays:
                await self.write("  No active stays found.\n")
            else:
                await self.write(f"  Found {len(stays)} active stay(s):\n\n")
                
                for i, stay in enumerate(stays, 1):
                    duration = self._format_duration(stay.get('duration', 0))
                    sessions_count = len(stay.get('sessions', []))
                    
                    await self.write(f"  [{i}] Stay #{stay['id']}\n")
                    await self.write(f"      User: {stay['user_name']}\n")
                    await self.write(f"      Started: {stay['started_at']}\n")
                    await self.write(f"      Duration: {duration}\n")
                    await self.write(f"      Sessions: {sessions_count}\n\n")
        
        except Exception as e:
            await self.write(f"\n⚠️  Error fetching stays: {e}\n")
            logger.error(f"Admin console: Error fetching stays: {e}", exc_info=True)
        
        await self.write("\n")
        await self.get_input("Press Enter to continue...")
        await self.clear_screen()
    
    async def show_active_sessions(self):
        """Show list of active sessions with join capability"""
        await self.clear_screen()
        await self.write("\n╔═══════════════════════════════════════════════════════════════════╗\n")
        await self.write("║                      ACTIVE SESSIONS                              ║\n")
        await self.write("╚═══════════════════════════════════════════════════════════════════╝\n\n")
        
        try:
            # Fetch active sessions from Tower API
            sessions = await asyncio.to_thread(self.tower.get_active_sessions)
            
            if not sessions:
                await self.write("  No active sessions found.\n")
            else:
                await self.write(f"  Found {len(sessions)} active session(s):\n\n")
                
                for i, sess in enumerate(sessions, 1):
                    duration = self._format_duration(sess.get('duration', 0))
                    protocol = sess.get('protocol', 'ssh').upper()
                    
                    await self.write(f"  [{i}] Session ID: {sess['session_id']}\n")
                    await self.write(f"      User: {sess['user_name']}\n")
                    await self.write(f"      Protocol: {protocol}\n")
                    await self.write(f"      Target: {sess.get('ssh_username', '')}@{sess.get('server_name', sess.get('backend_ip', 'unknown'))}\n")
                    await self.write(f"      Started: {sess['started_at']}\n")
                    await self.write(f"      Duration: {duration}\n")
                    await self.write(f"      Source: {sess.get('source_ip', 'unknown')}\n\n")
        
        except Exception as e:
            await self.write(f"\n⚠️  Error fetching sessions: {e}\n")
            logger.error(f"Admin console: Error fetching sessions: {e}", exc_info=True)
        
        await self.write("\n")
        await self.get_input("Press Enter to continue...")
        await self.clear_screen()
    
    async def join_session(self):
        """Join existing session (read-write mode)"""
        await self.clear_screen()
        await self.write("\n╔═══════════════════════════════════════════════════════════════════╗\n")
        await self.write("║                     JOIN SESSION (R/W)                            ║\n")
        await self.write("╚═══════════════════════════════════════════════════════════════════╝\n\n")
        
        try:
            sessions = await asyncio.to_thread(self.tower.get_active_sessions)
            
            if not sessions:
                await self.write("  No active sessions to join.\n")
                await self.get_input("\nPress Enter to continue...")
                await self.clear_screen()
                return
            
            # Show sessions with numbers
            await self.write("  Active sessions:\n\n")
            for i, sess in enumerate(sessions, 1):
                protocol = sess.get('protocol', 'ssh').upper()
                target = f"{sess.get('ssh_username', '')}@{sess.get('server_name', sess.get('backend_ip', 'unknown'))}"
                await self.write(f"  [{i}] {sess['user_name']} → {target} ({protocol})\n")
                await self.write(f"      Session ID: {sess['session_id']}\n\n")
            
            # Get user choice
            choice = await self.get_input("\nEnter session number (or 'q' to cancel): ")
            
            if choice.lower() == 'q':
                await self.clear_screen()
                return
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sessions):
                    session = sessions[idx]
                    await self.write(f"\n🔗 Joining session {session['session_id']}...\n")
                    await self.write("   (This will be implemented in the next step)\n")
                    
                    # TODO: Implement actual session joining
                    # await self.session_manager.join_session(
                    #     session['session_id'],
                    #     self.channel,
                    #     read_only=False
                    # )
                    
                    await asyncio.sleep(2)
                else:
                    await self.write("\n⚠️  Invalid session number.\n")
            except ValueError:
                await self.write("\n⚠️  Invalid input.\n")
        
        except Exception as e:
            await self.write(f"\n⚠️  Error: {e}\n")
            logger.error(f"Admin console: Error joining session: {e}", exc_info=True)
        
        await self.get_input("\nPress Enter to continue...")
        await self.clear_screen()
    
    async def watch_session(self):
        """Watch existing session (read-only mode)"""
        await self.clear_screen()
        await self.write("\n╔═══════════════════════════════════════════════════════════════════╗\n")
        await self.write("║                  WATCH SESSION (READ-ONLY)                        ║\n")
        await self.write("╚═══════════════════════════════════════════════════════════════════╝\n\n")
        
        await self.write("  This feature will allow read-only session monitoring.\n")
        await self.write("  Implementation coming soon...\n\n")
        
        # TODO: Similar to join_session but with read_only=True
        
        await self.get_input("Press Enter to continue...")
        await self.clear_screen()
    
    async def kill_session(self):
        """Kill active session"""
        await self.clear_screen()
        await self.write("\n╔═══════════════════════════════════════════════════════════════════╗\n")
        await self.write("║                       KILL SESSION                                ║\n")
        await self.write("╚═══════════════════════════════════════════════════════════════════╝\n\n")
        
        try:
            sessions = await asyncio.to_thread(self.tower.get_active_sessions)
            
            if not sessions:
                await self.write("  No active sessions.\n")
                await self.get_input("\nPress Enter to continue...")
                await self.clear_screen()
                return
            
            # Show sessions
            await self.write("  Active sessions:\n\n")
            for i, sess in enumerate(sessions, 1):
                target = f"{sess.get('ssh_username', '')}@{sess.get('server_name', sess.get('backend_ip', 'unknown'))}"
                await self.write(f"  [{i}] {sess['user_name']} → {target}\n")
                await self.write(f"      Session ID: {sess['session_id']}\n\n")
            
            # Get user choice
            choice = await self.get_input("\nEnter session number to kill (or 'q' to cancel): ")
            
            if choice.lower() == 'q':
                await self.clear_screen()
                return
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sessions):
                    session = sessions[idx]
                    
                    # Confirm
                    confirm = await self.get_input(f"\n⚠️  Really kill session {session['session_id']}? (yes/no): ")
                    
                    if confirm.lower() == 'yes':
                        await self.write(f"\n💀 Killing session {session['session_id']}...\n")
                        
                        # Use Tower API to terminate session
                        result = await asyncio.to_thread(self.tower.kill_session, session['session_id'])
                        
                        if result.get('success'):
                            await self.write("   ✅ Session terminated successfully.\n")
                        else:
                            await self.write(f"   ❌ Failed: {result.get('error', 'Unknown error')}\n")
                    else:
                        await self.write("\n  Cancelled.\n")
                else:
                    await self.write("\n⚠️  Invalid session number.\n")
            except ValueError:
                await self.write("\n⚠️  Invalid input.\n")
        
        except Exception as e:
            await self.write(f"\n⚠️  Error: {e}\n")
            logger.error(f"Admin console: Error killing session: {e}", exc_info=True)
        
        await self.get_input("\nPress Enter to continue...")
        await self.clear_screen()
    
    async def write(self, text: str):
        """Write text to channel"""
        if self.channel:
            self.channel.write(text)
    
    async def get_input(self, prompt: str = "") -> str:
        """Get input from user"""
        if prompt:
            await self.write(prompt)
        
        # Read line from channel
        buffer = ""
        while True:
            try:
                data = await asyncio.wait_for(self.channel.recv(1), timeout=300)  # 5 min timeout
                if not data:
                    return ""
                
                char = data.decode('utf-8', errors='ignore')
                
                if char == '\r' or char == '\n':
                    await self.write('\n')
                    return buffer.strip()
                elif char == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt()
                elif char == '\x7f' or char == '\x08':  # Backspace
                    if buffer:
                        buffer = buffer[:-1]
                        await self.write('\b \b')
                else:
                    buffer += char
                    await self.write(char)
            
            except asyncio.TimeoutError:
                await self.write("\n\nTimeout. Goodbye!\n")
                self.running = False
                return ""
            except KeyboardInterrupt:
                await self.write("\n\nInterrupted. Goodbye!\n")
                self.running = False
                return ""
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
