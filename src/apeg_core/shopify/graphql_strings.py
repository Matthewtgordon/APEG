"""Canonical GraphQL query/mutation strings for Shopify Admin API."""

# Phase 1: Bulk Query Operations
MUTATION_BULK_RUN_QUERY = """
mutation BulkRunQuery($query: String!) {
  bulkOperationRunQuery(query: $query) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

QUERY_BULK_OP_BY_ID = """
query BulkOpById($id: ID!) {
  node(id: $id) {
    ... on BulkOperation {
      id
      status
      errorCode
      objectCount
      url
      partialDataUrl
    }
  }
}
"""

# Phase 2: Bulk Mutation Operations
MUTATION_STAGED_UPLOADS_CREATE = """
mutation StagedUploadsCreateForBulkMutation($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    userErrors { field message }
    stagedTargets {
      url
      resourceUrl
      parameters { name value }
    }
  }
}
"""

MUTATION_BULK_OPERATION_RUN_MUTATION = """
mutation BulkOperationRunMutation(
  $mutation: String!,
  $stagedUploadPath: String!,
  $clientIdentifier: String
) {
  bulkOperationRunMutation(
    mutation: $mutation,
    stagedUploadPath: $stagedUploadPath,
    clientIdentifier: $clientIdentifier
  ) {
    bulkOperation { id status url }
    userErrors { field message }
  }
}
"""

MUTATION_PRODUCT_UPDATE = """
mutation call($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product {
      id
      tags
      seo { title description }
    }
    userErrors { field message }
  }
}
"""

QUERY_PRODUCTS_CURRENT_STATE = """
{
  products {
    edges {
      node {
        id
        tags
        seo {
          title
          description
        }
      }
    }
  }
}
"""
