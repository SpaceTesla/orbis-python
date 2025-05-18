pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'pip install pytest'
            }
        }
        
        stage('Test') {
            steps {
                sh 'pytest tests/test_dockerfile_generator.py -v'
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
} 