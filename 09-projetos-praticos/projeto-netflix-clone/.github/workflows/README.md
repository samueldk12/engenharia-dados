# CI/CD Workflows

Automated CI/CD pipelines for the Netflix Clone project using GitHub Actions.

## Workflows

### 1. Tests (`tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs:**
- **test**: Run unit and integration tests
  - Matrix strategy: Python 3.9, 3.10, 3.11
  - Services: PostgreSQL, Redis, Cassandra
  - Generate coverage reports
  - Upload to Codecov

- **lint**: Code quality checks
  - flake8 (style guide)
  - black (formatting)
  - mypy (type checking)
  - pylint (code analysis)

- **security**: Security scanning
  - safety (dependency vulnerabilities)
  - bandit (code security issues)

**Usage:**
```bash
# Runs automatically on push/PR
# View results in GitHub Actions tab
```

---

### 2. Performance Benchmarks (`performance.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main`
- Weekly schedule (Sundays 00:00 UTC)
- Manual trigger (`workflow_dispatch`)

**Jobs:**
- **benchmark-recommendations**: ML recommendation performance
  - Single prediction latency (<1ms target)
  - Batch throughput (>10K/s target)
  - Top-N recommendations (<50ms p99 target)

- **benchmark-analytics**: Analytics pipeline performance
  - Event processing throughput
  - QoE calculation speed
  - End-to-end latency

- **performance-tracking**: Store historical metrics
  - Track performance over time
  - Detect regressions

**Usage:**
```bash
# Automatic on push to main

# Manual trigger:
# GitHub Actions → Performance Benchmarks → Run workflow
```

**Performance Targets:**
- ✅ Prediction p99 < 1ms
- ✅ Batch throughput > 10,000/s
- ✅ Recommendation p99 < 50ms
- ✅ Analytics processing < 100ms

---

### 3. Docker Build and Push (`docker.yml`)

**Triggers:**
- Push to `main` branch
- Version tags (`v*`)
- Pull requests to `main`

**Jobs:**
- **build-and-push**: Build Docker images
  - Services: analytics-consumer, video-processor, recommendation-service
  - Push to GitHub Container Registry
  - Multi-platform builds
  - Layer caching

- **build-docker-compose**: Test full stack
  - Validate docker-compose.yml
  - Build all services
  - Run smoke tests

- **security-scan**: Container security
  - Hadolint (Dockerfile linting)
  - Trivy (vulnerability scanning)
  - TruffleHog (secrets detection)

**Usage:**
```bash
# Runs automatically on push to main

# Images pushed to:
# ghcr.io/[owner]/netflix-clone/analytics-consumer:latest
# ghcr.io/[owner]/netflix-clone/video-processor:latest
# ghcr.io/[owner]/netflix-clone/recommendation-service:latest
```

---

### 4. Deploy to Production (`deploy.yml`)

**Triggers:**
- Version tags (`v*`)
- Manual trigger with environment selection

**Jobs:**
- **deploy-staging**: Deploy to staging environment
  - AWS ECS deployment
  - Smoke tests
  - Slack notifications

- **deploy-production**: Blue-green production deployment
  - Deploy to green environment
  - Run comprehensive tests
  - Switch traffic gradually
  - Monitor metrics (5 minutes)
  - Auto-rollback on failure
  - Retire blue environment

- **post-deployment**: Post-deployment tasks
  - Invalidate CDN cache
  - Warm up Redis caches
  - Update monitoring dashboards

**Usage:**
```bash
# Automatic on version tags:
git tag v1.2.3
git push origin v1.2.3

# Manual deployment:
# GitHub Actions → Deploy to Production → Run workflow
# Select environment: staging or production
```

**Deployment Strategy:**
1. Deploy to staging
2. Run smoke tests
3. Deploy to production green environment
4. Run comprehensive tests
5. Switch traffic (blue → green)
6. Monitor for 5 minutes
7. Retire blue environment

**Rollback:**
- Automatic on test failure
- Manual via GitHub UI
- Switches traffic back to blue
- Zero downtime

---

## Setup

### Required Secrets

Configure in GitHub Settings → Secrets:

**AWS:**
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key

**Load Balancer:**
- `LB_LISTENER_ARN`: ALB listener ARN
- `BLUE_TARGET_GROUP_ARN`: Blue target group
- `GREEN_TARGET_GROUP_ARN`: Green target group

**CDN:**
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront distribution

**Monitoring:**
- `GRAFANA_API_KEY`: Grafana API key

**Notifications:**
- `SLACK_WEBHOOK`: Slack webhook URL

### Service Configuration

**ECS Clusters:**
- `netflix-clone-staging`: Staging cluster
- `netflix-clone-production`: Production cluster

**ECS Services:**
- `analytics-consumer`
- `recommendation-service`
- `video-processor`

**Environments:**
- staging: Pre-production testing
- production: Live production (blue-green)

---

## Workflow Matrix

| Workflow | On Push | On PR | On Tag | Schedule | Manual |
|----------|---------|-------|--------|----------|--------|
| Tests | ✅ | ✅ | ✅ | ❌ | ❌ |
| Performance | ✅ (main) | ✅ | ❌ | ✅ (weekly) | ✅ |
| Docker | ✅ (main) | ✅ | ✅ | ❌ | ❌ |
| Deploy | ❌ | ❌ | ✅ | ❌ | ✅ |

---

## Branch Protection

Recommended branch protection rules for `main`:

- ✅ Require pull request reviews (1+)
- ✅ Require status checks to pass:
  - test (Python 3.9, 3.10, 3.11)
  - lint
  - security
- ✅ Require branches to be up to date
- ✅ Require conversation resolution
- ❌ Allow force pushes
- ❌ Allow deletions

---

## Deployment Process

### 1. Development

```bash
git checkout -b feature/new-feature
# Make changes
git commit -m "feat: add new feature"
git push origin feature/new-feature
```

**Actions:**
- Tests run on PR
- Code review required
- Performance benchmarks run

### 2. Merge to Main

```bash
# After PR approval
git checkout main
git merge feature/new-feature
git push origin main
```

**Actions:**
- Full test suite runs
- Docker images built and pushed
- Automatic deploy to staging (optional)

### 3. Release to Production

```bash
# Create release tag
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

**Actions:**
- Deploy to staging
- Run smoke tests
- Deploy to production (blue-green)
- Monitor metrics
- Auto-rollback on failure

### 4. Hotfix

```bash
git checkout -b hotfix/critical-bug main
# Fix bug
git commit -m "fix: critical bug"
git push origin hotfix/critical-bug

# After PR approval:
git checkout main
git merge hotfix/critical-bug
git tag v1.2.4
git push origin v1.2.4
```

---

## Monitoring Deployments

### GitHub Actions UI

View deployment status:
1. Go to repository → Actions
2. Select workflow (Deploy to Production)
3. View logs and status

### Slack Notifications

Receive notifications for:
- ✅ Successful deployments
- ❌ Failed deployments
- ⚠️ Rollbacks

### Grafana Dashboards

Track deployment metrics:
- Error rates
- Response times
- Throughput
- Resource usage

---

## Troubleshooting

### Tests Failing

```bash
# Run tests locally
pytest tests/ -v

# Check specific test
pytest tests/test_recommendations.py::TestMatrixFactorization -v

# Check coverage
pytest tests/ --cov=. --cov-report=term
```

### Performance Regression

```bash
# Run benchmarks locally
python benchmarks/benchmark_recommendations.py
python benchmarks/benchmark_analytics.py

# Compare with baseline
# If p99 latency increased >10%, investigate:
# - Profile code (cProfile)
# - Check dependencies
# - Review recent changes
```

### Docker Build Failing

```bash
# Test build locally
docker-compose build

# Check specific service
docker build -f docker/analytics-consumer/Dockerfile .

# View logs
docker-compose logs analytics-consumer
```

### Deployment Failing

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster netflix-clone-production \
  --services analytics-consumer

# View task logs
aws logs tail /ecs/analytics-consumer --follow

# Manual rollback if needed
aws elbv2 modify-listener \
  --listener-arn $LB_LISTENER_ARN \
  --default-actions Type=forward,TargetGroupArn=$BLUE_TARGET_GROUP_ARN
```

---

## Best Practices

1. **Always create PRs** for changes (no direct commits to main)
2. **Run tests locally** before pushing
3. **Keep PRs small** (<500 lines)
4. **Write descriptive commit messages** (conventional commits)
5. **Tag releases** with semantic versioning (v1.2.3)
6. **Monitor deployments** for at least 5 minutes
7. **Document breaking changes** in PR description
8. **Test in staging** before production release

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS ECS Deployment](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/)
- [Blue-Green Deployments](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Semantic Versioning](https://semver.org/)
