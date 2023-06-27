properties ( [
    buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '', numToKeepStr: '5')),
    disableConcurrentBuilds(),
])

node ('macOS') {

    stage('Collect environment variables') {

        withCredentials([
            string(credentialsId: 'github-token', variable: 'GITHUB_TOKEN')
        ]) {
            env.GITHUB_TOKEN = "${GITHUB_TOKEN}"
        }
    }
        
    try { 
                    
        stage('Checkout - macOS') {
            checkout scm
        }
        
        stage('Build - macOS') {
            timeout(time: 10, unit: 'MINUTES') {
               sh '/bin/bash ./runjenk.sh'
            }
        }
        stage('Artifacts - macOS') {
            archiveArtifacts artifacts: '*.json', fingerprint: true
        }
    } catch (err) {
        mail body: "Build failed.\n\nSee: ${BUILD_URL}",
            to: emailextrecipients([[$class: 'CulpritsRecipientProvider']]),
            subject: "Build failed - Jenkins: ${currentBuild.fullDisplayName}"
        
        throw err
    }
}

