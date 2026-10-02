pipeline {
  agent none

  options {
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
    timestamps()
  }

  parameters {
    choice(name: 'LANE', choices: ['app-ci', 'model-promote'], description: 'Catalog lane')
    string(name: 'DEPLOYABLE', description: 'Name from configs/platform-deployables.yaml')
    string(name: 'IMAGE_REPOSITORY', description: 'Registry repository without a tag or digest')
    string(name: 'IMAGE_DIGEST', description: 'Immutable sha256:<64 lowercase hex> digest')
    string(name: 'SOURCE_SHA', description: '40-character source commit SHA')
    string(name: 'GITOPS_BASE_SHA', description: '40-character GitOps base commit SHA')
  }

  stages {
    stage('Catalog validation') {
      agent { label 'fsds-ci' }
      steps {
        checkout scm
        sh 'python -m scripts.ci.delivery catalog'
        sh 'python -m py_compile scripts/ci/catalog.py scripts/ci/gitops_paths.py scripts/ci/delivery.py'
        stash name: 'source', includes: 'src/**,scripts/**,tests/**,configs/**,pyproject.toml,uv.lock,Jenkinsfile', useDefaultExcludes: false
      }
    }

    stage('Build and verify') {
      agent { label 'fsds-ci' }
      steps {
        deleteDir()
        unstash 'source'
        sh 'python -m pytest tests/platform/verification/test_delivery_contract.py -q'
      }
    }

    stage('Digest handoff') {
      agent { label 'fsds-ci' }
      steps {
        deleteDir()
        unstash 'source'
        sh '''
          test -n "$DEPLOYABLE"
          test -n "$IMAGE_REPOSITORY"
          test -n "$IMAGE_DIGEST"
          test -n "$SOURCE_SHA"
          test -n "$GITOPS_BASE_SHA"
          python -m scripts.ci.delivery handoff \
            --deployable "$DEPLOYABLE" \
            --lane "$LANE" \
            --repository "$IMAGE_REPOSITORY" \
            --digest "$IMAGE_DIGEST" \
            --source-sha "$SOURCE_SHA" \
            --gitops-base-sha "$GITOPS_BASE_SHA" \
            --jenkins-build-id "$BUILD_TAG" \
            --output "delivery-${BUILD_NUMBER}.json"
        '''
        archiveArtifacts artifacts: 'delivery-*.json', fingerprint: true
      }
    }
  }

  post {
    aborted { echo 'Build cancelled; no GitOps or cluster mutation was attempted.' }
    failure { echo 'Build failed before any GitOps or cluster mutation was attempted.' }
  }
}
