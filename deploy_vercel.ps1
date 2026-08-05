# deploy_vercel.ps1
# Deploy to Vercel production from repo root
# Vercel project rootDirectory = lunyoro-translator/frontend (set in project settings)
# Run from repo root: .\deploy_vercel.ps1

Write-Host "Deploying to Vercel production..." -ForegroundColor Cyan
vercel deploy --prod --scope k227archs-projects 2>&1
Write-Host "Deploy complete." -ForegroundColor Green
