pipeline {
    agent {
        docker {
            image 'python:3.10-slim'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    
    environment {
        DOCKER_IMAGE = 'orbis-python'
        DOCKER_TAG = "${BUILD_NUMBER}"
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    pip install pytest pytest-asyncio
                '''
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
                    echo "Running tests..."
                    pytest tests/ -v
                '''
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}")
                }
            }
        }
        
        stage('Push Docker Image') {
            steps {
                script {
                    // Uncomment and configure these lines when you have a Docker registry
                    // docker.withRegistry('https://your-registry.com', 'docker-credentials') {
                    //     docker.image("${DOCKER_IMAGE}:${DOCKER_TAG}").push()
                    // }
                }
            }
        }
        
        stage('Deploy') {
            steps {
                sh '''
                    docker-compose down || true
                    docker-compose up -d
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
