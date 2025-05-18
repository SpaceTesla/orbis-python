pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip
                    pip3 install pytest
                '''
            }
        }
        
        stage('Test') {
            steps {
                sh '''
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