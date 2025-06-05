pipeline {
    agent any
    environment {
        PATH = "/usr/local/bin:${env.PATH}"
    }

    stages {
        stage('Checkout') {
            steps {
                ws('/Users/fmarzullo/Development/BairesDev/ehp-core') {
                    checkout scm
                }
            }
        }
        stage('Install Dependencies') {
            steps {
                ws('/Users/fmarzullo/Development/BairesDev/ehp-core') {
                    echo "Installing dependencies..."
                    // Check if the virtual environment exists; if not, create it.
                    sh '''
                        if [ ! -d ".venv" ]; then
                          echo "Virtual environment not found. Creating .venv..."
                          python3 -m venv .venv
                        fi
                        echo "Activating virtual environment and installing dependencies..."
                        source .venv/bin/activate
                        pip install -r requirements/requirements.txt
                    '''
                }
            }
        }
//         stage('Run Tests') {
//             steps {
//                 ws('/Users/fmarzullo/Development/BairesDev/ehp-core') {
//                     echo "Running tests..."
//                     sh 'pytest --maxfail=1 --disable-warnings -q'
//                 }
//             }
//         }
        stage('Restart Docker Compose') {
            steps {
                ws('/Users/fmarzullo/Development/BairesDev/ehp-core') {
                    echo "Restarting Docker Compose services..."
                    sh 'docker compose down'
                    sh 'docker compose build'
                    sh 'docker compose up -d'
                }
            }
        }
    }

    post {
        success {
            echo "Deployment completed successfully!"
        }
        failure {
            echo "Deployment failed. Please check the logs."
        }
    }
}
