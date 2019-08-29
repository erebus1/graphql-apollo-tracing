import os
from setuptools import setup


def read(*rnames):
  return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


setup(
  name = 'graphql-apollo-tracing',
  packages = ['graphql_apollo_tracing'],
  version = '0.0.1',
  license='MIT',
  description = 'tracing federated service',
  long_description=(read('README.md')),
  long_description_content_type='text/markdown',
  author = 'Igor Kasianov',
  author_email = 'super.hang.glider@gmail.com',
  url = 'https://github.com/erebus1/graphql-apollo-tracing',
  download_url = 'https://github.com/erebus1/graphql-apollo-tracing/archive/0.0.1.tar.gz',
  keywords = ['graphene', 'gql', 'federation', 'tracing'],
  install_requires=[
          "graphql-core>=2.2.0,<3"
      ],
  classifiers=[
    'Development Status :: 3 - Alpha',
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries",
    "Programming Language :: Python :: 3.6",
  ],
)