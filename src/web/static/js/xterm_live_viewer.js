/**
 * Live Session Viewer with xterm.js + WebSocket
 * Replaces legacy JSON polling with real-time terminal streaming
 */

// Initialize live view when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initLiveSessionViewer();
});

function initLiveSessionViewer() {
    const toggleLiveBtn = document.getElementById('toggle-live');
    if (!toggleLiveBtn) {
        return;  // No live view button on this page
    }
    
    let socket = null;
    let terminal = null;
    let isLiveActive = false;
    
    const xtermContainer = document.getElementById('xterm-container');
    const legacyLogViewer = document.querySelector('.terminal-container');
    const sessionId = toggleLiveBtn.dataset.sessionId;  // Session ID from button data attribute
    const isSessionActive = toggleLiveBtn.dataset.isActive === 'true';
    
    toggleLiveBtn.addEventListener('click', function() {
        if (!isLiveActive) {
            startLiveView();
        } else {
            stopLiveView();
        }
    });
    
    function startLiveView() {
        console.log('[xterm.js] Starting live view for session:', sessionId);
        
        // Update button
        toggleLiveBtn.innerHTML = '<i class="bi bi-stop-circle"></i> Stop Live View';
        toggleLiveBtn.classList.remove('btn-success');
        toggleLiveBtn.classList.add('btn-danger');
        isLiveActive = true;
        
        // Show xterm container, hide legacy viewer
        if (xtermContainer) {
            xtermContainer.style.display = 'block';
        }
        if (legacyLogViewer) {
            legacyLogViewer.style.display = 'none';
        }
        
        // Initialize xterm.js terminal
        terminal = new Terminal({
            cursorBlink: false,
            scrollback: 10000,
            fontSize: 14,
            fontFamily: '"Courier New", Courier, monospace',
            theme: {
                background: '#000000',
                foreground: '#ffffff',
                cursor: '#ffffff',
                cursorAccent: '#000000',
                selection: 'rgba(255, 255, 255, 0.3)',
                black: '#000000',
                red: '#cd0000',
                green: '#00cd00',
                yellow: '#cdcd00',
                blue: '#0000ee',
                magenta: '#cd00cd',
                cyan: '#00cdcd',
                white: '#e5e5e5',
                brightBlack: '#7f7f7f',
                brightRed: '#ff0000',
                brightGreen: '#00ff00',
                brightYellow: '#ffff00',
                brightBlue: '#5c5cff',
                brightMagenta: '#ff00ff',
                brightCyan: '#00ffff',
                brightWhite: '#ffffff'
            },
            // Watch-only mode: disable input
            disableStdin: true
        });
        
        terminal.open(document.getElementById('xterm-terminal'));
        
        // Show banner
        terminal.writeln('\x1b[1;32m========================================\x1b[0m');
        terminal.writeln('\x1b[1;37m  Inside Live Session View (xterm.js)\x1b[0m');
        terminal.writeln('\x1b[1;32m========================================\x1b[0m');
        terminal.writeln('');
        terminal.writeln('\x1b[33mConnecting to WebSocket...\x1b[0m');
        terminal.writeln('');
        
        // Initialize Socket.IO
        // Use polling first (WebSocket upgrade may fail behind reverse proxy)
        socket = io({
            transports: ['polling', 'websocket'],
            upgrade: true,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: 5
        });
        
        // Connection events
        socket.on('connect', function() {
            console.log('[WebSocket] Connected, requesting session access...');
            terminal.writeln('\x1b[32m✓ WebSocket connected\x1b[0m');
            terminal.writeln('');
            
            // Request to watch session
            socket.emit('watch_session', {
                session_id: sessionId,
                mode: 'watch'  // read-only (join mode in v2.1)
            });
        });
        
        socket.on('watch_started', function(data) {
            console.log('[WebSocket] Watch started:', data);
            terminal.writeln('\x1b[1;36m' + data.message + '\x1b[0m');
            if (data.gate) {
                terminal.writeln('\x1b[2mGate: ' + data.gate + ' | Owner: ' + data.owner + ' | Server: ' + data.server + '\x1b[0m');
            } else {
                terminal.writeln('\x1b[2mOwner: ' + data.owner + ' | Server: ' + data.server + '\x1b[0m');
            }
            terminal.writeln('');
            terminal.writeln('\x1b[2m--- Session History (50KB buffer) ---\x1b[0m');
            terminal.writeln('');
        });
        
        socket.on('relay_pending', function(data) {
            // Session is on gate - waiting for relay activation (~5s)
            console.log('[WebSocket] Relay pending:', data);
            terminal.writeln('\x1b[1;33m⏳ ' + data.message + '\x1b[0m');
            terminal.writeln('\x1b[2mGate: ' + data.gate_name + '\x1b[0m');
            terminal.writeln('');
        });
        
        socket.on('relay_activated', function(data) {
            // Gate relay now active - connection imminent
            console.log('[WebSocket] Relay activated:', data);
            terminal.writeln('\x1b[1;32m✓ ' + data.message + '\x1b[0m');
            terminal.writeln('');
        });
        
        socket.on('session_output', function(data) {
            // Receive output from SessionMultiplexer via WebSocketChannelAdapter
            // data.data is array of bytes (converted from Python bytes object)
            if (data.data && data.data.length > 0) {
                const bytes = new Uint8Array(data.data);
                terminal.write(bytes);
            }
        });
        
        socket.on('session_ended', function(data) {
            console.log('[WebSocket] Session ended:', data);
            terminal.writeln('');
            terminal.writeln('');
            terminal.writeln('\x1b[1;31m========================================\x1b[0m');
            terminal.writeln('\x1b[1;31m       Session Ended\x1b[0m');
            terminal.writeln('\x1b[1;31m========================================\x1b[0m');
            
            // Auto-stop live view and reload to show full recording
            setTimeout(function() {
                stopLiveView();
                window.location.reload();
            }, 3000);
        });
        
        socket.on('error', function(data) {
            console.error('[WebSocket] Error:', data);
            terminal.writeln('');
            terminal.writeln('\x1b[1;31m✗ Error: ' + data.message + '\x1b[0m');
            
            // Session running on remote gate (distributed architecture)
            if (data.reason === 'distributed_architecture') {
                terminal.writeln('');
                terminal.writeln('\x1b[1;33m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m');
                terminal.writeln('\x1b[1;36mℹ  How to watch this session:\x1b[0m');
                terminal.writeln('');
                terminal.writeln('\x1b[37m  This session is running on a remote gate.\x1b[0m');
                terminal.writeln('\x1b[37m  Web live view only works for Tower sessions.\x1b[0m');
                terminal.writeln('');
                terminal.writeln('\x1b[1;32m  Use SSH admin console to watch:\x1b[0m');
                terminal.writeln('\x1b[37m    $ ssh admin@jumphost\x1b[0m');
                terminal.writeln('');
                terminal.writeln('\x1b[1;33m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m');
                setTimeout(function() {
                    stopLiveView();
                }, 8000);  // 8s to read message
            }
            // Legacy session (no multiplexer support)
            else if (data.fallback === 'json_polling') {
                terminal.writeln('');
                terminal.writeln('\x1b[33mThis is a legacy session without multiplexer support.\x1b[0m');
                terminal.writeln('\x1b[33mPlease refresh the page to view the recording.\x1b[0m');
                setTimeout(function() {
                    stopLiveView();
                }, 3000);
            }
            // Other errors
            else {
                setTimeout(function() {
                    stopLiveView();
                }, 3000);
            }
        });
        
        socket.on('disconnect', function(reason) {
            console.log('[WebSocket] Disconnected:', reason);
            terminal.writeln('');
            terminal.writeln('\x1b[1;33m✗ Disconnected: ' + reason + '\x1b[0m');
        });
        
        socket.on('connected', function(data) {
            console.log('[WebSocket] Connected event:', data);
        });
    }
    
    function stopLiveView() {
        console.log('[xterm.js] Stopping live view...');
        
        // Update button
        toggleLiveBtn.innerHTML = '<i class="bi bi-play-circle"></i> Start Live View';
        toggleLiveBtn.classList.remove('btn-danger');
        toggleLiveBtn.classList.add('btn-success');
        isLiveActive = false;
        
        // Hide xterm container, show legacy viewer
        if (xtermContainer) {
            xtermContainer.style.display = 'none';
        }
        if (legacyLogViewer) {
            legacyLogViewer.style.display = 'block';
        }
        
        // Disconnect WebSocket
        if (socket) {
            socket.disconnect();
            socket = null;
        }
        
        // Destroy terminal
        if (terminal) {
            terminal.dispose();
            terminal = null;
        }
    }
    
    // Auto-start live view for active sessions
    if (isSessionActive) {
        console.log('[xterm.js] Session is active - auto-starting live view');
        setTimeout(function() {
            toggleLiveBtn.click();
        }, 500);  // Small delay to ensure DOM is ready
    }
}
