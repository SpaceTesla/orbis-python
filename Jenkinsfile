pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    
    environment {
        DOCKER_BUILDKIT = '1'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python -m pip install --upgrade pip
                    pip install pytest
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
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
} 