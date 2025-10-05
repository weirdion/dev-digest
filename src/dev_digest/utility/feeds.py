from typing import List

AWS_FEEDS: List[str] = [
    "https://aws.amazon.com/blogs/aws/feed/",                              # AWS News Blog
    "https://aws.amazon.com/about-aws/whats-new/recent/feed/",             # What's New at AWS (service launches)
    "https://aws.amazon.com/security/security-bulletins/feed/",            # Security Bulletins
    "https://aws.amazon.com/blogs/architecture/feed/",                     # Architecture Blog
    "https://aws.amazon.com/blogs/compute/feed/",                          # Compute (Lambda, EC2, etc.)
    "https://aws.amazon.com/blogs/containers/feed/",                       # Containers (ECS/EKS/Fargate)
    "https://aws.amazon.com/blogs/database/feed/",                         # Database Blog (RDS, DynamoDB)
    "https://aws.amazon.com/blogs/networking-and-content-delivery/feed/",  # VPC/Networking/CDN
    "https://aws.amazon.com/blogs/opensource/feed/",                       # Open Source @ AWS
    "https://aws.amazon.com/blogs/devops/feed/",                           # DevOps & Developer Productivity
]

LAST_WEEK_AWS: List[str] = [
    "https://www.lastweekinaws.com/blog/feed/",                      # Last Week in AWS Blog
    "https://www.lastweekinaws.com/newsletter/feed/"                 # Last Week in AWS Newsletter
]

IAC_FEEDS: List[str] = [
    "https://www.hashicorp.com/blog/products/terraform/feed",        # Terraform
    "https://www.pulumi.com/blog/index.xml",                         # Pulumi Blog
    "https://github.com/aws/aws-cdk/releases.atom",                  # AWS CDK releases (GitHub Atom)
    "https://github.com/hashicorp/terraform/releases.atom",          # Terraform releases (GitHub Atom)
]

KUBERNETES_FEEDS: List[str] = [
    "https://kubernetes.io/feed.xml",                                # Kubernetes Blog
    "https://helm.sh/blog/feed",                                     # Helm Blog
    "https://istio.io/blog/feed.xml",                                # Istio Blog
    "https://www.cncf.io/blog/feed/",                                # CNCF Blog (ecosystem)
]

PYTHON_FEEDS: List[str] = [
    "https://blog.python.org/feeds/posts/default",                   # Python Insider (release notes)
    "https://realpython.com/atom.xml",                               # Real Python blog
#    "https://pyfound.blogspot.com/feeds/posts/default",              # PSF (Foundation) Blog
]

BACKEND_FEEDS: List[str] = [
    "https://www.uber.com/blog/engineering/rss/",                    # Uber Engineering
    "https://githubengineering.com/atom.xml",                        # GitHub Engineering
    # "https://thenewstack.io/feed/",                                  # The New Stack (cloud-native)
    "https://blog.cloudflare.com/feed/",                             # Cloudflare engineering/product
]

AI_FEEDS: List[str] = [
    "https://openai.com/blog/rss.xml",                               # OpenAI Blog
    "https://deepmind.google/blog/rss.xml",                          # Google AI Blog
    "https://aws.amazon.com/blogs/machine-learning/feed/",           # AWS Machine Learning Blog
]

ARS_TECHNICAL_BLOGS: List[str] = [
    "https://arstechnica.com/security/feed/",                        # Ars Technica Security
    "https://arstechnica.com/ai/feed/",                              # Ars Technica AI
]

# disabled for now - too noisy
REGISTER_FEEDS: List[str] = [
    # "https://www.theregister.com/software/headlines.atom"            # The Register - All Software
]

ALL_FEEDS: List[str] = AWS_FEEDS + \
                       LAST_WEEK_AWS + \
                       IAC_FEEDS + \
                       KUBERNETES_FEEDS + \
                       PYTHON_FEEDS + \
                       BACKEND_FEEDS + \
                       AI_FEEDS + \
                       ARS_TECHNICAL_BLOGS
