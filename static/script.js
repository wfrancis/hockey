// Global variables
let currentStats = {};
let actionHistory = []; // stack of {playerNum, statType, change}
const MAX_HISTORY = 25;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadCurrentStats();
    setupEventListeners();
    setupStatCellGestures();
});

function setupEventListeners() {
    document.getElementById('resetBtn').addEventListener('click', resetAllStats);
    document.getElementById('exportBtn').addEventListener('click', exportSummary);
    const undoBtn = document.getElementById('undoBtn');
    if (undoBtn) {
        undoBtn.addEventListener('click', undoLastAction);
    }

    // Prevent stat cell gesture from triggering when pressing +/- buttons
    document.querySelectorAll('.stat-controls .btn').forEach(btn => {
        ['click', 'mousedown', 'touchstart'].forEach(evt =>
            btn.addEventListener(evt, e => e.stopPropagation(), { passive: true })
        );
    });
}

async function loadCurrentStats() {
    try {
        const response = await fetch('/api/get_stats');
        const data = await response.json();
        currentStats = data.stats;
        updateTotals();
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function modifyStat(playerNum, statType, change, options = { recordHistory: true }) {
    try {
        const key = playerNum.toString();
        const prevVal = currentStats[key] ? currentStats[key][statType] : undefined;
        const response = await fetch('/api/update_stat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                player_num: playerNum,
                stat_type: statType,
                change: change
            })
        });

        const data = await response.json();

        if (data.success) {
            // Update the display
            document.getElementById(`${statType}_${playerNum}`).textContent = data.new_value;

            // Update local stats
            currentStats[key][statType] = data.new_value;

            // Update totals
            updateTotals();

            // Add visual feedback
            const element = document.getElementById(`${statType}_${playerNum}`);
            element.classList.add('stat-updated');
            setTimeout(() => {
                element.classList.remove('stat-updated');
            }, 300);

            // History and status
            if (options.recordHistory !== false && prevVal !== data.new_value) {
                actionHistory.push({ playerNum, statType, change });
                if (actionHistory.length > MAX_HISTORY) actionHistory.shift();
                setStatus(`Updated #${playerNum} ${labelFromType(statType)} ${change > 0 ? '+1' : '-1'}`, true);
            } else if (options.recordHistory === false) {
                setStatus('Undo applied', actionHistory.length > 0);
            } else {
                setStatus('No change', actionHistory.length > 0);
            }
        }
    } catch (error) {
        console.error('Error updating stat:', error);
        setStatus('Error updating stat', actionHistory.length > 0);
        alert('Error updating stat. Please try again.');
    }
}

function quickAction(playerNum, statType, change = 1) {
    modifyStat(playerNum, statType, change);
}

function labelFromType(t) {
    switch (t) {
        case 'plus_minus':
            return 'Plus/Minus';
        case 'blocked_shots':
            return 'Blocked Shots';
        case 'takeaways':
            return 'Takeaways';
        default:
            return t;
    }
}

function setStatus(text, showUndo = false) {
    const indicator = document.getElementById('statusIndicator');
    if (!indicator) return;
    const textEl = indicator.querySelector('.status-text');
    if (textEl) textEl.textContent = text;
    const undoBtn = document.getElementById('undoBtn');
    if (undoBtn) {
        undoBtn.style.display = showUndo ? 'inline-flex' : 'none';
    }
}

async function undoLastAction() {
    const last = actionHistory.pop();
    if (!last) {
        setStatus('Nothing to undo', false);
        return;
    }
    await modifyStat(last.playerNum, last.statType, -last.change, { recordHistory: false });
}

async function resetAllStats() {
    if (!confirm('Are you sure you want to reset all stats to zero?')) {
        return;
    }

    try {
        const response = await fetch('/api/reset_stats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.success) {
            // Update all displays
            currentStats = data.stats;

            // Update all stat displays
            Object.keys(currentStats).forEach(playerNum => {
                document.getElementById(`plus_minus_${playerNum}`).textContent = '0';
                document.getElementById(`blocked_shots_${playerNum}`).textContent = '0';
                document.getElementById(`takeaways_${playerNum}`).textContent = '0';
            });

            // Update totals
            updateTotals();

            // Clear history and update status
            actionHistory = [];
            setStatus('All stats have been reset to zero.', false);
            alert('All stats have been reset to zero.');
        }
    } catch (error) {
        console.error('Error resetting stats:', error);
        setStatus('Error resetting stats', false);
        alert('Error resetting stats. Please try again.');
    }
}

function updateTotals() {
    let totalPlusMinus = 0;
    let totalBlocked = 0;
    let totalTakeaways = 0;

    Object.values(currentStats).forEach(playerStats => {
        totalPlusMinus += playerStats.plus_minus;
        totalBlocked += playerStats.blocked_shots;
        totalTakeaways += playerStats.takeaways;
    });

    document.getElementById('total-plus-minus').textContent = totalPlusMinus;
    document.getElementById('total-blocked').textContent = totalBlocked;
    document.getElementById('total-takeaways').textContent = totalTakeaways;
}

async function exportSummary() {
    try {
        const response = await fetch('/api/export_summary');

        if (response.ok) {
            // Create a blob from the response and trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.headers.get('Content-Disposition').split('filename=')[1];
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            setStatus('Summary exported', actionHistory.length > 0);
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        console.error('Error exporting summary:', error);
        setStatus('Error exporting summary', actionHistory.length > 0);
        alert('Error exporting summary. Please try again.');
    }
}

// Add CSS animation class
const style = document.createElement('style');
style.textContent = `
    .stat-updated {
        background-color: #27ae60 !important;
        color: white !important;
        transform: scale(1.1);
        transition: all 0.3s ease;
    }
`;
document.head.appendChild(style);

// Gesture support on stat cells: tap to +1, long-press to -1
function setupStatCellGestures() {
    const cells = document.querySelectorAll('.player-row .stat-cell');
    cells.forEach(cell => {
        const statType = cell.dataset.stat;
        if (!statType) return;
        const row = cell.closest('.player-row');
        if (!row) return;
        const playerNum = parseInt(row.dataset.player, 10);

        let longPressTimer = null;
        let longPressTriggered = false;

        const start = () => {
            longPressTriggered = false;
            clearTimeout(longPressTimer);
            longPressTimer = setTimeout(() => {
                longPressTriggered = true;
                modifyStat(playerNum, statType, -1);
            }, 550);
        };

        const end = () => {
            clearTimeout(longPressTimer);
            if (!longPressTriggered) {
                modifyStat(playerNum, statType, 1);
            }
        };

        cell.addEventListener('mousedown', start);
        cell.addEventListener('mouseup', end);
        cell.addEventListener('mouseleave', () => clearTimeout(longPressTimer));
        cell.addEventListener('touchstart', start, { passive: true });
        cell.addEventListener('touchend', end);
        cell.addEventListener('touchcancel', () => clearTimeout(longPressTimer));

        // Do not let inner buttons propagate events to the cell
        cell.querySelectorAll('button').forEach(btn => {
            ['click', 'mousedown', 'touchstart'].forEach(evt =>
                btn.addEventListener(evt, e => e.stopPropagation(), { passive: true })
            );
        });
    });
}