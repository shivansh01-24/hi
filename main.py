import json
import os
import logging
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import optimizer
import ai_insights
import quantum_optimizer
import quantum_playground
import openai_insights
import file_parser
import config

# Set up logging
config.setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "qeo-development-key")

# Enable CORS for security
CORS(app, resources={r"/*": {"origins": "*"}})

# Set up rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize quantum optimizer and OpenAI insights generator
ibm_token = config.IBM_QUANTUM_TOKEN
openai_key = config.OPENAI_API_KEY

# Validate API keys (basic validation)
if ibm_token and (len(ibm_token) < 20 or ibm_token.startswith('Your IBM')):
    logger.warning("IBM Quantum token appears invalid - disabling quantum features")
    ibm_token = None
    
if not openai_key:
    logger.warning("No OpenAI API key found - disabling OpenAI features")
    openai_key = None
# We'll accept any non-empty key that's at least 32 characters
elif len(openai_key) < 32:
    logger.warning("OpenAI API key appears too short - disabling OpenAI features")
    openai_key = None

# Track if we're using quantum computing and/or OpenAI
use_quantum = ibm_token is not None
use_openai = openai_key is not None

if use_quantum:
    logger.info("IBM Quantum token found - will attempt to use quantum computing")
else:
    logger.info("No IBM Quantum token found - using classical optimization")

if use_openai:
    logger.info("OpenAI API key found - will use GPT for insights")
else:
    logger.info("No OpenAI API key found - using deterministic insights")

# Initialize our optimizers and insight generators
quantum_opt = quantum_optimizer.QuantumWorkflowOptimizer(use_quantum=use_quantum, ibm_token=ibm_token)
openai_gen = openai_insights.OpenAIInsightsGenerator(api_key=openai_key)
quantum_playground_instance = quantum_playground.QuantumPlayground(use_real_quantum=use_quantum, ibm_token=ibm_token)

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html')

@app.route('/data-format')
def data_format():
    """Render the data format guide page"""
    return render_template('data_format.html')

@app.route('/import-file', methods=['POST'])
def import_file():
    """Process file upload and extract project and developer data"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
            
        if file:
            # Read the file content
            file_content = file.read()
            
            # Parse the file based on its type
            result = file_parser.parse_uploaded_file(file_content, file.filename)
            
            if not result.get('success', False):
                logger.error(f"File parsing error: {result.get('error', 'Unknown error')}")
                return jsonify(result), 400
                
            logger.info(f"Successfully imported data from file: {file.filename}")
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        return jsonify({'success': False, 'error': f'File upload failed: {str(e)}'}), 500

@app.route('/optimize', methods=['POST'])
def optimize():
    """Process optimization request and return results"""
    try:
        # Get input data from request
        data = request.json
        logger.info(f"Received optimization request with {len(data.get('developers', []))} developers and {len(data.get('projects', []))} projects")
        
        # Validate input data
        if not _validate_input(data):
            logger.error("Input validation failed")
            return jsonify({'success': False, 'error': 'Invalid input data'}), 400
        
        # Check if we should try quantum optimization
        use_quantum_param = request.args.get('quantum', 'true').lower() == 'true'
        
        try:
            if use_quantum and use_quantum_param:
                # Run quantum-powered optimization algorithm
                logger.info("Using quantum-powered optimization")
                optimization_result = quantum_opt.optimize(
                    data['budget'],
                    data['deadline'],
                    data['developers'],
                    data['projects']
                )
            else:
                # Run classical optimization algorithm
                logger.info("Using classical optimization")
                optimization_result = optimizer.run_optimization(
                    data['budget'],
                    data['deadline'],
                    data['developers'],
                    data['projects']
                )
                
            logger.info(f"Optimization completed successfully with {len(optimization_result.get('assignments', []))} assignments")
        except Exception as opt_error:
            logger.error(f"Optimization algorithm failed: {str(opt_error)}")
            return jsonify({'success': False, 'error': f'Optimization algorithm failed: {str(opt_error)}'}), 500
        
        try:
            # Generate AI insights - try OpenAI first, fall back to deterministic
            if use_openai:
                logger.info("Generating OpenAI-powered insights")
                insights = openai_gen.generate_insights(
                    data, 
                    optimization_result
                )
            else:
                logger.info("Using deterministic insights")
                insights = ai_insights.generate_insights(
                    data, 
                    optimization_result
                )
            
            logger.info("Insights generation completed successfully")
        except Exception as insights_error:
            logger.error(f"Insights generation failed: {str(insights_error)}")
            # Fall back to deterministic insights on failure
            insights = ai_insights.generate_insights(
                data, 
                optimization_result
            )
        
        # Combine results
        result = {**optimization_result, **{'success': True}, **insights}
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in optimization process: {str(e)}")
        return jsonify({'success': False, 'error': f'Optimization failed: {str(e)}'}), 500

def _validate_input(data):
    """Validate the input data"""
    try:
        # Check required fields
        required_fields = ['budget', 'deadline', 'developers', 'projects']
        for field in required_fields:
            if field not in data:
                logging.error(f"Missing required field: {field}")
                return False
        
        # Validate numeric values
        if not isinstance(data['budget'], (int, float)) or data['budget'] <= 0:
            logging.error("Budget must be a positive number")
            return False
        
        if not isinstance(data['deadline'], (int, float)) or data['deadline'] <= 0:
            logging.error("Deadline must be a positive number")
            return False
        
        # Validate developers
        if not isinstance(data['developers'], list) or len(data['developers']) == 0:
            logging.error("At least one developer is required")
            return False
        
        for dev in data['developers']:
            if not all(key in dev for key in ['name', 'rate', 'hours_per_day', 'skills']):
                logging.error("Developer missing required fields")
                return False
            if not isinstance(dev['rate'], (int, float)) or dev['rate'] <= 0:
                logging.error("Developer rate must be a positive number")
                return False
            if not isinstance(dev['hours_per_day'], (int, float)) or dev['hours_per_day'] <= 0:
                logging.error("Developer hours_per_day must be a positive number")
                return False
        
        # Validate projects
        if not isinstance(data['projects'], list) or len(data['projects']) == 0:
            logging.error("At least one project is required")
            return False
        
        for proj in data['projects']:
            if not all(key in proj for key in ['name', 'hours', 'priority']):
                logging.error("Project missing required fields")
                return False
            if not isinstance(proj['hours'], (int, float)) or proj['hours'] <= 0:
                logging.error("Project hours must be a positive number")
                return False
            if not isinstance(proj['priority'], (int, float)) or proj['priority'] < 1 or proj['priority'] > 5:
                logging.error("Project priority must be between 1 and 5")
                return False
        
        return True
    
    except Exception as e:
        logging.error(f"Validation error: {str(e)}")
        return False

@app.route('/quantum-playground')
def quantum_playground_page():
    """Render the quantum playground page"""
    # Get available backends
    backends = quantum_playground_instance.get_available_backends()
    return render_template('quantum_playground.html', backends=backends)

@app.route('/quantum/create-circuit', methods=['POST'])
def create_quantum_circuit():
    """Create a quantum circuit based on the specified parameters"""
    try:
        # Get input data from request
        data = request.json
        num_qubits = data.get('num_qubits', 2)
        circuit_type = data.get('circuit_type', 'empty')
        
        # Validate input
        if not isinstance(num_qubits, int) or num_qubits < 1 or num_qubits > 12:
            return jsonify({'success': False, 'error': 'Invalid number of qubits'}), 400
            
        # Create the circuit
        result = quantum_playground_instance.create_circuit(num_qubits, circuit_type)
        
        if not result.get('success', False):
            logger.error(f"Circuit creation error: {result.get('error', 'Unknown error')}")
            return jsonify(result), 400
            
        logger.info(f"Successfully created {circuit_type} circuit with {num_qubits} qubits")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error creating quantum circuit: {str(e)}")
        return jsonify({'success': False, 'error': f'Circuit creation failed: {str(e)}'}), 500

@app.route('/quantum/run-circuit', methods=['POST'])
def run_quantum_circuit():
    """Run a quantum circuit simulation"""
    try:
        # Get input data from request
        data = request.json
        circuit = data.get('circuit')
        backend = data.get('backend', 'qasm_simulator')
        shots = data.get('shots', 1024)
        
        # Validate input
        if not circuit:
            return jsonify({'success': False, 'error': 'No circuit provided'}), 400
            
        if not isinstance(shots, int) or shots < 1 or shots > 10000:
            return jsonify({'success': False, 'error': 'Shots must be between 1 and 10,000'}), 400
            
        # Run the circuit
        result = quantum_playground_instance.run_circuit(circuit, backend, shots)
        
        if not result.get('success', False):
            logger.error(f"Circuit simulation error: {result.get('error', 'Unknown error')}")
            return jsonify(result), 400
            
        logger.info(f"Successfully ran circuit simulation on {backend} with {shots} shots")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error running quantum circuit: {str(e)}")
        return jsonify({'success': False, 'error': f'Circuit simulation failed: {str(e)}'}), 500

@app.route('/quantum/backends', methods=['GET'])
def get_quantum_backends():
    """Get a list of available quantum backends"""
    try:
        backends = quantum_playground_instance.get_available_backends()
        return jsonify({'success': True, 'backends': backends})
    except Exception as e:
        logger.error(f"Error getting quantum backends: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to get backends: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
