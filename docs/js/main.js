// Load and display regime data

async function loadData() {
    try {
        const response = await fetch('data/regime_data.json');
        const data = await response.json();
        
        console.log('Loaded data:', data);
        
        updateCurrentRegime(data.current, data.meta);
        updatePeriodStats(data.period_stats);
        updateRegimeStats(data.regime_stats);
        updateLastSwitch(data.last_switch);
        
        // Render multiple timeline charts
        renderTimelineChart('timelineChart7d', data.history['7d'], '7-Day');
        renderTimelineChart('timelineChart30d', data.history['30d'], '30-Day');
        renderTimelineChart('timelineChart100d', data.history['100d'], '100-Day');
        renderTimelineChart('timelineChart365d', data.history['365d'], '1-Year');
        
        // Render calendar heatmap
        renderCalendarHeatmap(data.calendar);
        
        // Render historical events table
        renderEventsTable(data.historical_events);
        
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('regimeLabel').textContent = 'Error Loading Data';
    }
}

function updateCurrentRegime(current, meta) {
    // Update time
    document.getElementById('updateTime').textContent = 
        `Last updated: ${meta.last_update}`;
    
    // Update data freshness indicator
    const freshnessDiv = document.getElementById('dataFreshness');
    if (meta.data_freshness === 'up-to-date') {
        freshnessDiv.textContent = `✅ Data: ${meta.data_date} (Up-to-date)`;
        freshnessDiv.className = 'data-freshness fresh';
    } else {
        freshnessDiv.textContent = `⚠️ Data: ${meta.data_date} (Historical)`;
        freshnessDiv.className = 'data-freshness stale';
    }
    
    // Update regime indicator
    const regimeCard = document.getElementById('regimeCard');
    const regimeIcon = document.getElementById('regimeIcon');
    const regimeLabel = document.getElementById('regimeLabel');
    
    regimeCard.className = `regime-card ${current.regime}`;
    regimeLabel.textContent = current.regime.toUpperCase();
    regimeIcon.textContent = current.regime === 'fear' ? '🔴' : '🟢';
    
    // Update confidence
    document.getElementById('confidence').textContent = current.confidence;
    
    // Update metrics
    document.getElementById('btcPrice').textContent = 
        `$${current.btc_price.toLocaleString()}`;
    document.getElementById('fgIndex').textContent = current.fg_index;
    document.getElementById('volatility').textContent = current.volatility_7d.toFixed(4);
    document.getElementById('breadth').textContent = `${current.market_breadth}%`;
}

function updatePeriodStats(stats) {
    // Week
    updatePeriod('week', stats.week);
    
    // Month
    updatePeriod('month', stats.month);
    
    // Quarter
    updatePeriod('quarter', stats.quarter);
}

function updatePeriod(period, data) {
    document.getElementById(`${period}Fear`).style.width = `${data.fear_pct}%`;
    document.getElementById(`${period}Greed`).style.width = `${data.greed_pct}%`;
    document.getElementById(`${period}FearPct`).textContent = `${data.fear_pct}%`;
    document.getElementById(`${period}GreedPct`).textContent = `${data.greed_pct}%`;
    document.getElementById(`${period}Switches`).textContent = data.switches;
}

function updateRegimeStats(stats) {
    document.getElementById('avgFearDuration').textContent = stats.avg_fear_duration.toFixed(1);
    document.getElementById('avgGreedDuration').textContent = stats.avg_greed_duration.toFixed(1);
    document.getElementById('totalSwitches').textContent = stats.total_switches;
    document.getElementById('currentDuration').textContent = stats.current_duration;
}

function updateLastSwitch(switchData) {
    const switchDiv = document.getElementById('lastSwitch');
    
    if (switchData && switchData.date) {
        switchDiv.style.display = 'block';
        document.getElementById('switchDate').textContent = switchData.date;
        document.getElementById('switchDays').textContent = switchData.days_ago;
    } else {
        switchDiv.style.display = 'none';
    }
}

function renderTimelineChart(canvasId, history, label) {
    const ctx = document.getElementById(canvasId);
    
    // Prepare data
    const dates = history.map(h => h.date);
    const prices = history.map(h => h.btc_price);
    const regimes = history.map(h => h.regime);
    
    // Create point colors
    const pointColors = regimes.map(r => 
        r === 'fear' ? 'rgba(255, 71, 87, 1)' : 'rgba(46, 213, 115, 1)'
    );
    
    // Create point styles - different shapes for fear and greed
    const pointStyles = regimes.map(r => 
        r === 'fear' ? 'triangle' : 'rectRot'  // triangle for fear (down), diamond for greed (up)
    );
    
    // Point sizes
    const baseRadius = canvasId === 'timelineChart365d' ? 3 : 6;
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: `BTC Price (${label})`,
                data: prices,
                borderColor: '#00d2d3',
                backgroundColor: 'rgba(0, 210, 211, 0.1)',
                borderWidth: 2,
                pointBackgroundColor: pointColors,
                pointBorderColor: pointColors,
                pointStyle: pointStyles,
                pointRadius: baseRadius,
                pointHoverRadius: baseRadius + 3,
                pointBorderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#e0e0e0',
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#e0e0e0',
                    bodyColor: '#e0e0e0',
                    borderColor: '#00d2d3',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const regime = regimes[index];
                            const price = prices[index];
                            return [
                                `Price: $${price.toLocaleString()}`,
                                `Regime: ${regime.toUpperCase()}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#a0a0a0',
                        maxRotation: 45,
                        minRotation: 45,
                        maxTicksLimit: canvasId === 'timelineChart365d' ? 12 : 
                                      canvasId === 'timelineChart100d' ? 15 : 20
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        color: '#a0a0a0',
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

function renderEventsTable(events) {
    const tbody = document.getElementById('eventsTableBody');
    const accuracyDiv = document.getElementById('eventsAccuracy');
    
    if (!events || events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #a0a0a0;">No historical events data available</td></tr>';
        return;
    }
    
    // Calculate accuracy
    const matches = events.filter(e => e.is_match).length;
    const accuracy = (matches / events.length * 100).toFixed(1);
    
    accuracyDiv.textContent = `Model Accuracy: ${matches}/${events.length} (${accuracy}%)`;
    
    // Render table rows
    tbody.innerHTML = events.map(event => `
        <tr>
            <td>${event.date}</td>
            <td class="event-name">${event.name}</td>
            <td class="event-description">${event.description}</td>
            <td>
                <span class="regime-badge ${event.type}">${event.type.toUpperCase()}</span>
            </td>
            <td>
                <span class="regime-badge ${event.predicted_regime}">${event.predicted_regime.toUpperCase()}</span>
            </td>
            <td class="confidence-value">${event.confidence}%</td>
            <td class="result-icon ${event.is_match ? 'match' : 'mismatch'}">
                ${event.is_match ? '✓' : '✗'}
            </td>
        </tr>
    `).join('');
}

function renderCalendarHeatmap(calendarData) {
    const container = document.getElementById('calendarContainer');
    
    if (!calendarData || calendarData.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #a0a0a0;">No calendar data available</p>';
        return;
    }
    
    // Group data by year and month
    const dataByYear = {};
    
    calendarData.forEach(day => {
        const date = new Date(day.date);
        const year = date.getFullYear();
        const month = date.getMonth(); // 0-11
        
        if (!dataByYear[year]) {
            dataByYear[year] = {};
        }
        if (!dataByYear[year][month]) {
            dataByYear[year][month] = [];
        }
        dataByYear[year][month].push(day);
    });
    
    // Render calendar
    const years = Object.keys(dataByYear).sort((a, b) => b - a); // Latest year first
    
    container.innerHTML = years.map(year => {
        const monthsHtml = Object.keys(dataByYear[year])
            .sort((a, b) => b - a) // Latest month first
            .map(month => {
                const monthName = new Date(year, month, 1).toLocaleDateString('en-US', { month: 'long' });
                const days = dataByYear[year][month];
                
                // Get first day of month to calculate padding
                const firstDay = new Date(year, month, 1).getDay(); // 0 = Sunday
                const daysInMonth = new Date(year, parseInt(month) + 1, 0).getDate();
                
                // Create array with empty cells for padding + actual days
                const allCells = [];
                
                // Add empty cells for days before month starts
                for (let i = 0; i < firstDay; i++) {
                    allCells.push('<div class="calendar-day empty"></div>');
                }
                
                // Add actual days
                for (let dayNum = 1; dayNum <= daysInMonth; dayNum++) {
                    const dayData = days.find(d => new Date(d.date).getDate() === dayNum);
                    
                    if (dayData) {
                        const opacity = dayData.confidence / 100;
                        const bgColor = dayData.regime === 'fear' 
                            ? `rgba(255, 71, 87, ${0.3 + opacity * 0.7})` 
                            : `rgba(46, 213, 115, ${0.3 + opacity * 0.7})`;
                        
                        allCells.push(`
                            <div class="calendar-day ${dayData.regime}" 
                                 style="background: ${bgColor};"
                                 title="${dayData.date}: ${dayData.regime.toUpperCase()} (${dayData.confidence}% confidence, BTC: $${dayData.btc_price.toLocaleString()})">
                            </div>
                        `);
                    } else {
                        allCells.push('<div class="calendar-day empty"></div>');
                    }
                }
                
                return `
                    <div class="calendar-month">
                        <div class="calendar-month-header">${monthName}</div>
                        <div class="calendar-grid">
                            ${allCells.join('')}
                        </div>
                    </div>
                `;
            }).join('');
        
        return `
            <div class="calendar-year">
                <div class="calendar-year-header">${year}</div>
                <div class="calendar-months">
                    ${monthsHtml}
                </div>
            </div>
        `;
    }).join('');
}

// Load data when page loads
window.addEventListener('DOMContentLoaded', loadData);
