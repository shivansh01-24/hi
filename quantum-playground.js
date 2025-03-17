/**
 * Quantum Playground JavaScript functionality
 * Controls the quantum circuit builder and simulation interface
 */

// Global variables
let currentCircuit = null;
let resultsChart = null;

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize event listeners
    document.getElementById('create-circuit').addEventListener('click', createCircuit);
    document.getElementById('run-circuit').addEventListener('click', runCircuit);
    
    // Initialize the interface
    updateCircuitStatus('Ready to create a quantum circuit');
    
    // Initialize feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
});

/**
 * Create a quantum circuit based on the selected parameters
 */
async function createCircuit() {
    // Get user-selected parameters
    const numQubits = parseInt(document.getElementById('num-qubits').value);
    const circuitType = document.getElementById('circuit-type').value;
    
    // Validate inputs
    if (isNaN(numQubits) || numQubits < 1 || numQubits > 12) {
        updateCircuitStatus('Number of qubits must be between 1 and 12', 'error');
        return;
    }
    
    // Update UI
    updateCircuitStatus('Creating circuit...', 'loading');
    document.getElementById('run-circuit').disabled = true;
    document.getElementById('results-container').classList.add('hidden');
    
    try {
        // Make API request to create circuit
        const response = await fetch('/quantum/create-circuit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                num_qubits: numQubits,
                circuit_type: circuitType
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Store the circuit data
            currentCircuit = data.circuit;
            
            // Update the circuit diagram
            const circuitDiagram = document.getElementById('circuit-diagram');
            circuitDiagram.textContent = data.circuit_drawing;
            
            // Enable the run button
            document.getElementById('run-circuit').disabled = false;
            
            // Update status
            updateCircuitStatus(`${capitalize(circuitType)} circuit created with ${numQubits} qubits`, 'success');
        } else {
            updateCircuitStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Circuit creation error:', error);
        updateCircuitStatus('Failed to create circuit due to a server error', 'error');
    }
}

/**
 * Run the current quantum circuit on the selected backend
 */
async function runCircuit() {
    // Check if we have a circuit
    if (!currentCircuit) {
        updateCircuitStatus('No circuit to run. Create a circuit first.', 'error');
        return;
    }
    
    // Get simulation parameters
    const backend = document.getElementById('backend-select').value;
    const shots = parseInt(document.getElementById('shots').value);
    
    // Validate inputs
    if (isNaN(shots) || shots < 1 || shots > 10000) {
        updateCircuitStatus('Shots must be between 1 and 10,000', 'error');
        return;
    }
    
    // Update UI
    updateCircuitStatus('Running quantum simulation...', 'loading');
    document.getElementById('run-circuit').disabled = true;
    
    try {
        // Make API request to run the circuit
        const response = await fetch('/quantum/run-circuit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                circuit: currentCircuit,
                backend: backend,
                shots: shots
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Display the results
            displayResults(data);
            
            // Update status
            const backendDisplay = backend.includes('simulator') 
                ? `${capitalize(backend)}` 
                : `IBM Q device: ${backend}`;
                
            updateCircuitStatus(
                `Simulation completed on ${backendDisplay} with ${shots} shots`, 
                'success'
            );
        } else {
            updateCircuitStatus(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Simulation error:', error);
        updateCircuitStatus('Failed to run simulation due to a server error', 'error');
    } finally {
        // Re-enable the run button
        document.getElementById('run-circuit').disabled = false;
    }
}

/**
 * Display the circuit simulation results
 */
function displayResults(results) {
    // Show the results container
    document.getElementById('results-container').classList.remove('hidden');
    
    // Update the results summary
    const summaryElement = document.getElementById('results-summary');
    const counts = results.counts;
    
    // Build the summary HTML
    let summaryHtml = '<div class="counts-display">';
    
    // Add backend information
    summaryHtml += `<p><strong>Backend:</strong> ${results.backend}</p>`;
    summaryHtml += `<p><strong>Shots:</strong> ${results.shots}</p>`;
    
    // Add quantum indicator if available
    if (results.quantum_powered) {
        summaryHtml += '<p class="quantum-indicator">Using Quantum Computation</p>';
    }
    
    // Add counts table
    summaryHtml += '<table class="counts-table"><thead><tr><th>Outcome</th><th>Count</th><th>Probability</th></tr></thead><tbody>';
    
    const histogramData = results.histogram_data;
    for (let i = 0; i < histogramData.labels.length; i++) {
        const label = histogramData.labels[i];
        const count = histogramData.values[i];
        const prob = histogramData.probabilities[i];
        
        summaryHtml += `<tr>
            <td>${label}</td>
            <td>${count}</td>
            <td>${(prob * 100).toFixed(2)}%</td>
        </tr>`;
    }
    
    summaryHtml += '</tbody></table></div>';
    summaryElement.innerHTML = summaryHtml;
    
    // Update the chart
    updateResultsChart(histogramData);
}

/**
 * Update the results visualization chart
 */
function updateResultsChart(histogramData) {
    const ctx = document.getElementById('results-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (resultsChart) {
        resultsChart.destroy();
    }
    
    // Create a new chart
    resultsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: histogramData.labels,
            datasets: [{
                label: 'Counts',
                data: histogramData.values,
                backgroundColor: getQuantumGradientColors(histogramData.labels.length),
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Measurement Outcomes'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const count = context.raw;
                            const probability = histogramData.probabilities[context.dataIndex];
                            return `Count: ${count} (${(probability * 100).toFixed(2)}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Count'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Bitstring'
                    }
                }
            }
        }
    });
}

/**
 * Generate a gradient of colors for the quantum states
 */
function getQuantumGradientColors(numColors) {
    const colors = [];
    
    // Define a quantum-inspired gradient
    const baseColors = [
        'rgba(0, 63, 92, 0.7)',    // Deep blue
        'rgba(88, 80, 141, 0.7)',  // Indigo
        'rgba(188, 80, 144, 0.7)', // Purple
        'rgba(255, 99, 97, 0.7)',  // Red-pink
        'rgba(255, 166, 0, 0.7)'   // Gold
    ];
    
    // For a small number of colors, use a subset
    if (numColors <= baseColors.length) {
        return baseColors.slice(0, numColors);
    }
    
    // For more colors, interpolate
    for (let i = 0; i < numColors; i++) {
        const ratio = i / (numColors - 1);
        const colorIndex = Math.min(Math.floor(ratio * (baseColors.length - 1)), baseColors.length - 2);
        const blendRatio = (ratio * (baseColors.length - 1)) - colorIndex;
        
        // Get the two colors to blend
        const color1 = parseRgba(baseColors[colorIndex]);
        const color2 = parseRgba(baseColors[colorIndex + 1]);
        
        // Blend the colors
        const blendedColor = blendColors(color1, color2, blendRatio);
        colors.push(blendedColor);
    }
    
    return colors;
}

/**
 * Parse an RGBA color string into components
 */
function parseRgba(rgbaString) {
    const match = rgbaString.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)/);
    if (match) {
        return {
            r: parseInt(match[1]),
            g: parseInt(match[2]),
            b: parseInt(match[3]),
            a: parseFloat(match[4])
        };
    }
    return { r: 0, g: 0, b: 0, a: 1 };
}

/**
 * Blend two colors based on a ratio
 */
function blendColors(color1, color2, ratio) {
    const r = Math.round(color1.r + (color2.r - color1.r) * ratio);
    const g = Math.round(color1.g + (color2.g - color1.g) * ratio);
    const b = Math.round(color1.b + (color2.b - color1.b) * ratio);
    const a = color1.a + (color2.a - color1.a) * ratio;
    
    return `rgba(${r}, ${g}, ${b}, ${a})`;
}

/**
 * Update the circuit status message
 */
function updateCircuitStatus(message, status = 'info') {
    const statusElement = document.getElementById('circuit-status');
    
    // Clear existing status classes
    statusElement.classList.remove('status-info', 'status-success', 'status-error', 'status-loading');
    
    // Add appropriate status class
    statusElement.classList.add(`status-${status}`);
    
    // Update the message
    statusElement.textContent = message;
}

/**
 * Capitalize the first letter of a string
 */
function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}