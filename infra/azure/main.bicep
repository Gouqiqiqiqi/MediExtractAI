// ──────────────────────────────────────────────────────────────────────────────
// MediExtractAI — Azure Infrastructure (Bicep)
// Deploys: App Service Plan, Web Apps, SQL, Storage, Key Vault, OpenAI
// Region: UK South (NHS compliant)
// ──────────────────────────────────────────────────────────────────────────────

targetScope = 'resourceGroup'

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure AD Tenant ID')
param tenantId string

@description('Azure AD Client ID for the app')
param clientId string

@secure()
@description('Azure AD Client Secret')
param clientSecret string

@description('SQL Administrator login')
param sqlAdminLogin string = 'sqladmin'

@secure()
@description('SQL Administrator password')
param sqlAdminPassword string

param location string = 'uksouth'
param prefix string = 'mediextract'

var suffix = '${prefix}-${environment}'

// ── App Service Plan ──
resource appPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${suffix}-plan'
  location: location
  sku: {
    name: environment == 'prod' ? 'P1v3' : 'B1'
    tier: environment == 'prod' ? 'PremiumV3' : 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// ── Backend Web App ──
resource backendApp 'Microsoft.Web/sites@2023-12-01' = {
  name: '${suffix}-api'
  location: location
  properties: {
    serverFarmId: appPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${suffix}api:latest'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      alwaysOn: true
      appSettings: [
        { name: 'AZURE_TENANT_ID', value: tenantId }
        { name: 'AZURE_CLIENT_ID', value: clientId }
        { name: 'AZURE_KEYVAULT_URL', value: keyVault.properties.vaultUri }
        { name: 'AZURE_OPENAI_ENDPOINT', value: openAi.properties.endpoint }
        { name: 'AZURE_STORAGE_CONTAINER', value: 'uploads' }
        { name: 'APP_ENV', value: environment == 'prod' ? 'production' : 'development' }
      ]
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ── Frontend Static Web App ──
resource frontendApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: '${suffix}-web'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    buildProperties: {
      appLocation: '/frontend'
      outputLocation: 'dist'
    }
  }
}

// ── Azure SQL Server + Database ──
resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: '${suffix}-sql'
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled'
  }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: '${suffix}-db'
  location: location
  sku: {
    name: environment == 'prod' ? 'S2' : 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: environment == 'prod' ? 268435456000 : 2147483648
  }
}

// ── Storage Account (for file uploads) ──
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: replace('${suffix}storage', '-', '')
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storage.name}/default/uploads'
  properties: {
    publicAccess: 'None'
  }
}

// ── Azure Key Vault ──
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${suffix}-kv'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
  }
}

// ── Azure OpenAI ──
resource openAi 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${suffix}-openai'
  location: location
  sku: { name: 'S0' }
  kind: 'OpenAI'
  properties: {
    publicNetworkAccess: 'Disabled'
    customSubDomainName: '${suffix}-openai'
  }
}

resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAi
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

// ── Outputs ──
output backendUrl string = 'https://${backendApp.properties.defaultHostName}'
output frontendUrl string = 'https://${frontendApp.properties.defaultHostname}'
output keyVaultUri string = keyVault.properties.vaultUri
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
