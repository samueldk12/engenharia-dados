#!/usr/bin/env python3
"""
Netflix Clone - Storage Lifecycle Policies
==========================================

Automated storage lifecycle management para otimização de custos.

Estratégias:
- Hot content (< 30 dias): Standard storage
- Warm content (30-90 dias): Infrequent Access
- Cold content (90-180 dias): Glacier
- Archive (> 365 dias): Deep Archive
- Source files: Delete após 30 dias (já transcodificados)
- Logs: Glacier após 30 dias, Deep Archive após 365

Savings estimados:
- Standard: $0.023/GB/mês
- IA: $0.0125/GB/mês (46% economia)
- Glacier: $0.004/GB/mês (83% economia)
- Deep Archive: $0.00099/GB/mês (96% economia)

Author: Data Engineering Study Project
"""

import boto3
from google.cloud import storage as gcs
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LifecycleRule:
    """Lifecycle rule configuration"""
    id: str
    prefix: str
    status: str  # 'Enabled' or 'Disabled'
    transitions: List[Dict]  # List of transitions
    expiration: Optional[Dict] = None

    def to_dict(self):
        rule = {
            'ID': self.id,
            'Prefix': self.prefix,
            'Status': self.status,
            'Transitions': self.transitions
        }
        if self.expiration:
            rule['Expiration'] = self.expiration
        return rule


class S3LifecycleManager:
    """
    Manage S3 lifecycle policies
    """

    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)

        logger.info(f"S3 Lifecycle Manager initialized: {bucket_name}")

    def create_content_lifecycle_policy(self) -> bool:
        """
        Create lifecycle policy for video content

        Strategy:
        - Hot content (0-30 days): STANDARD
        - Warm content (30-90 days): STANDARD_IA
        - Cold content (90-180 days): GLACIER_IR (Instant Retrieval)
        - Archive (>180 days): GLACIER
        """
        logger.info("Creating content lifecycle policy...")

        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'TransitionHotContent',
                    'Status': 'Enabled',
                    'Prefix': 'content/',
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER_IR'  # Instant Retrieval
                        },
                        {
                            'Days': 180,
                            'StorageClass': 'GLACIER'
                        }
                    ],
                    'NoncurrentVersionTransitions': [
                        {
                            'NoncurrentDays': 7,
                            'StorageClass': 'GLACIER_IR'
                        }
                    ]
                },
                {
                    'ID': 'DeleteRawContent',
                    'Status': 'Enabled',
                    'Prefix': 'raw-content/',
                    'Expiration': {
                        'Days': 30  # Delete source after 30 days
                    }
                },
                {
                    'ID': 'TransitionLogs',
                    'Status': 'Enabled',
                    'Prefix': 'logs/',
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'GLACIER_IR'
                        },
                        {
                            'Days': 365,
                            'StorageClass': 'DEEP_ARCHIVE'
                        }
                    ]
                },
                {
                    'ID': 'DeleteTempFiles',
                    'Status': 'Enabled',
                    'Prefix': 'temp/',
                    'Expiration': {
                        'Days': 7  # Delete temp files after 7 days
                    }
                },
                {
                    'ID': 'TransitionThumbnails',
                    'Status': 'Enabled',
                    'Prefix': 'thumbnails/',
                    'Transitions': [
                        {
                            'Days': 90,
                            'StorageClass': 'STANDARD_IA'
                        }
                    ]
                },
                {
                    'ID': 'AbortIncompleteMultipartUploads',
                    'Status': 'Enabled',
                    'Prefix': '',
                    'AbortIncompleteMultipartUpload': {
                        'DaysAfterInitiation': 7
                    }
                }
            ]
        }

        try:
            response = self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )

            logger.info("✓ Content lifecycle policy created successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to create lifecycle policy: {e}")
            return False

    def create_custom_rule(self, rule: LifecycleRule) -> bool:
        """Add custom lifecycle rule"""
        try:
            # Get existing configuration
            try:
                response = self.s3_client.get_bucket_lifecycle_configuration(
                    Bucket=self.bucket_name
                )
                rules = response['Rules']
            except self.s3_client.exceptions.NoSuchLifecycleConfiguration:
                rules = []

            # Add new rule
            rules.append(rule.to_dict())

            # Update configuration
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration={'Rules': rules}
            )

            logger.info(f"✓ Added lifecycle rule: {rule.id}")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to add rule: {e}")
            return False

    def get_lifecycle_configuration(self) -> Optional[Dict]:
        """Get current lifecycle configuration"""
        try:
            response = self.s3_client.get_bucket_lifecycle_configuration(
                Bucket=self.bucket_name
            )
            return response
        except self.s3_client.exceptions.NoSuchLifecycleConfiguration:
            logger.info("No lifecycle configuration found")
            return None
        except Exception as e:
            logger.error(f"Failed to get lifecycle configuration: {e}")
            return None

    def delete_lifecycle_configuration(self) -> bool:
        """Delete all lifecycle rules"""
        try:
            self.s3_client.delete_bucket_lifecycle(
                Bucket=self.bucket_name
            )
            logger.info("✓ Lifecycle configuration deleted")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to delete lifecycle configuration: {e}")
            return False

    def analyze_storage_costs(self) -> Dict:
        """
        Analyze storage costs by storage class

        Returns cost breakdown and savings from lifecycle policies
        """
        logger.info("Analyzing storage costs...")

        # Get storage metrics from CloudWatch
        cloudwatch = boto3.client('cloudwatch', region_name=self.region)

        # Get bucket size by storage class
        storage_classes = [
            'StandardStorage',
            'IntelligentTieringStorage',
            'StandardIAStorage',
            'GlacierInstantRetrievalStorage',
            'GlacierStorage',
            'DeepArchiveStorage'
        ]

        costs = {}
        total_size_gb = 0

        for storage_class in storage_classes:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName='BucketSizeBytes',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': self.bucket_name},
                        {'Name': 'StorageType', 'Value': storage_class}
                    ],
                    StartTime=datetime.utcnow() - timedelta(days=1),
                    EndTime=datetime.utcnow(),
                    Period=86400,
                    Statistics=['Average']
                )

                if response['Datapoints']:
                    size_bytes = response['Datapoints'][0]['Average']
                    size_gb = size_bytes / (1024**3)
                    total_size_gb += size_gb

                    # Calculate monthly cost
                    price_per_gb = self._get_storage_price(storage_class)
                    monthly_cost = size_gb * price_per_gb

                    costs[storage_class] = {
                        'size_gb': size_gb,
                        'price_per_gb': price_per_gb,
                        'monthly_cost': monthly_cost
                    }

            except Exception as e:
                logger.warning(f"Failed to get metrics for {storage_class}: {e}")

        # Calculate total cost and potential savings
        total_cost = sum(c['monthly_cost'] for c in costs.values())

        # Calculate cost if everything was in Standard
        standard_price = 0.023
        standard_cost = total_size_gb * standard_price

        savings = standard_cost - total_cost
        savings_percentage = (savings / standard_cost * 100) if standard_cost > 0 else 0

        result = {
            'bucket_name': self.bucket_name,
            'total_size_gb': total_size_gb,
            'total_monthly_cost': total_cost,
            'standard_cost': standard_cost,
            'monthly_savings': savings,
            'savings_percentage': savings_percentage,
            'storage_classes': costs
        }

        logger.info(f"Total size: {total_size_gb:.2f} GB")
        logger.info(f"Monthly cost: ${total_cost:.2f}")
        logger.info(f"Savings: ${savings:.2f} ({savings_percentage:.1f}%)")

        return result

    def _get_storage_price(self, storage_class: str) -> float:
        """Get price per GB/month for storage class (us-east-1 pricing)"""
        prices = {
            'StandardStorage': 0.023,
            'IntelligentTieringStorage': 0.023,  # Same as Standard, but with monitoring fee
            'StandardIAStorage': 0.0125,
            'GlacierInstantRetrievalStorage': 0.004,
            'GlacierStorage': 0.0036,
            'DeepArchiveStorage': 0.00099
        }
        return prices.get(storage_class, 0.023)


class GCSLifecycleManager:
    """
    Manage Google Cloud Storage lifecycle policies
    """

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = gcs.Client()
        self.bucket = self.client.bucket(bucket_name)

        logger.info(f"GCS Lifecycle Manager initialized: {bucket_name}")

    def create_content_lifecycle_policy(self) -> bool:
        """
        Create lifecycle policy for GCS

        GCS storage classes:
        - STANDARD
        - NEARLINE (access < 1/month, min 30 days)
        - COLDLINE (access < 1/quarter, min 90 days)
        - ARCHIVE (access < 1/year, min 365 days)
        """
        logger.info("Creating GCS lifecycle policy...")

        try:
            # Define lifecycle rules
            rules = [
                # Hot content → Nearline after 30 days
                {
                    'action': {'type': 'SetStorageClass', 'storageClass': 'NEARLINE'},
                    'condition': {
                        'age': 30,
                        'matchesPrefix': ['content/']
                    }
                },
                # Warm content → Coldline after 90 days
                {
                    'action': {'type': 'SetStorageClass', 'storageClass': 'COLDLINE'},
                    'condition': {
                        'age': 90,
                        'matchesPrefix': ['content/']
                    }
                },
                # Cold content → Archive after 180 days
                {
                    'action': {'type': 'SetStorageClass', 'storageClass': 'ARCHIVE'},
                    'condition': {
                        'age': 180,
                        'matchesPrefix': ['content/']
                    }
                },
                # Delete raw content after 30 days
                {
                    'action': {'type': 'Delete'},
                    'condition': {
                        'age': 30,
                        'matchesPrefix': ['raw-content/']
                    }
                },
                # Logs → Archive after 365 days
                {
                    'action': {'type': 'SetStorageClass', 'storageClass': 'ARCHIVE'},
                    'condition': {
                        'age': 365,
                        'matchesPrefix': ['logs/']
                    }
                },
                # Delete temp files after 7 days
                {
                    'action': {'type': 'Delete'},
                    'condition': {
                        'age': 7,
                        'matchesPrefix': ['temp/']
                    }
                }
            ]

            # Apply lifecycle rules
            self.bucket.lifecycle_rules = rules
            self.bucket.patch()

            logger.info("✓ GCS lifecycle policy created successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to create GCS lifecycle policy: {e}")
            return False

    def get_lifecycle_configuration(self) -> Optional[List[Dict]]:
        """Get current lifecycle configuration"""
        try:
            self.bucket.reload()
            return list(self.bucket.lifecycle_rules)
        except Exception as e:
            logger.error(f"Failed to get lifecycle configuration: {e}")
            return None

    def delete_lifecycle_configuration(self) -> bool:
        """Delete all lifecycle rules"""
        try:
            self.bucket.lifecycle_rules = []
            self.bucket.patch()
            logger.info("✓ GCS lifecycle configuration deleted")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to delete lifecycle configuration: {e}")
            return False


def calculate_savings(total_size_gb: float, content_age_distribution: Dict[str, float]) -> Dict:
    """
    Calculate cost savings from lifecycle policies

    Args:
        total_size_gb: Total storage size in GB
        content_age_distribution: Distribution of content by age
            e.g., {'hot': 0.2, 'warm': 0.3, 'cold': 0.3, 'archive': 0.2}

    Returns:
        Dictionary with cost breakdown
    """
    # S3 pricing (us-east-1)
    prices = {
        'standard': 0.023,
        'ia': 0.0125,
        'glacier_ir': 0.004,
        'glacier': 0.0036,
        'deep_archive': 0.00099
    }

    # Without lifecycle policies (all Standard)
    cost_no_lifecycle = total_size_gb * prices['standard']

    # With lifecycle policies
    hot_size = total_size_gb * content_age_distribution.get('hot', 0.2)  # 0-30 days
    warm_size = total_size_gb * content_age_distribution.get('warm', 0.3)  # 30-90 days
    cold_size = total_size_gb * content_age_distribution.get('cold', 0.3)  # 90-180 days
    archive_size = total_size_gb * content_age_distribution.get('archive', 0.2)  # >180 days

    cost_with_lifecycle = (
        hot_size * prices['standard'] +
        warm_size * prices['ia'] +
        cold_size * prices['glacier_ir'] +
        archive_size * prices['glacier']
    )

    monthly_savings = cost_no_lifecycle - cost_with_lifecycle
    annual_savings = monthly_savings * 12

    return {
        'total_size_gb': total_size_gb,
        'cost_without_lifecycle': cost_no_lifecycle,
        'cost_with_lifecycle': cost_with_lifecycle,
        'monthly_savings': monthly_savings,
        'annual_savings': annual_savings,
        'savings_percentage': (monthly_savings / cost_no_lifecycle * 100) if cost_no_lifecycle > 0 else 0,
        'breakdown': {
            'hot': {'size_gb': hot_size, 'cost': hot_size * prices['standard']},
            'warm': {'size_gb': warm_size, 'cost': warm_size * prices['ia']},
            'cold': {'size_gb': cold_size, 'cost': cold_size * prices['glacier_ir']},
            'archive': {'size_gb': archive_size, 'cost': archive_size * prices['glacier']}
        }
    }


# Example usage
if __name__ == '__main__':
    # S3 Example
    s3_lifecycle = S3LifecycleManager(
        bucket_name='netflix-content-prod',
        region='us-east-1'
    )

    # Create content lifecycle policy
    s3_lifecycle.create_content_lifecycle_policy()

    # Get current configuration
    config = s3_lifecycle.get_lifecycle_configuration()
    if config:
        print(json.dumps(config, indent=2))

    # Analyze costs
    cost_analysis = s3_lifecycle.analyze_storage_costs()
    print("\nCost Analysis:")
    print(json.dumps(cost_analysis, indent=2))

    # Calculate potential savings for 1 PB of content
    print("\n" + "="*60)
    print("SAVINGS CALCULATOR - 1 PB Content Library")
    print("="*60)

    savings = calculate_savings(
        total_size_gb=1_000_000,  # 1 PB
        content_age_distribution={
            'hot': 0.15,      # 15% hot (new releases)
            'warm': 0.25,     # 25% warm (recent)
            'cold': 0.35,     # 35% cold (older)
            'archive': 0.25   # 25% archive (catalog)
        }
    )

    print(f"Total Size:              {savings['total_size_gb']:,} GB (1 PB)")
    print(f"Cost without lifecycle:  ${savings['cost_without_lifecycle']:,.2f}/month")
    print(f"Cost with lifecycle:     ${savings['cost_with_lifecycle']:,.2f}/month")
    print(f"Monthly Savings:         ${savings['monthly_savings']:,.2f}")
    print(f"Annual Savings:          ${savings['annual_savings']:,.2f}")
    print(f"Savings Percentage:      {savings['savings_percentage']:.1f}%")
    print("\nBreakdown:")
    for tier, data in savings['breakdown'].items():
        print(f"  {tier.capitalize():10} {data['size_gb']:>10,.0f} GB → ${data['cost']:>10,.2f}")
    print("="*60)
