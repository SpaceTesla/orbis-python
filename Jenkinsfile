pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install pytest
                '''
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
                    echo "Running tests..."
                    pytest tests/test_dockerfile_generator.py -v
                '''
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
} 