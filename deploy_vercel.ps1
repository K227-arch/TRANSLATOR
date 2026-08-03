# deploy_vercel.ps1
# Deploy the frontend to Vercel production
# Run from repo root: .\deploy_vercel.ps1

Write-Host "Deploying to Vercel production..." -ForegroundColor Cyan
Set-Location "lunyoro-translator\frontend"
vercel deploy --prod --scope k227archs-projects .
Set-Location "..\..\"
Write-Host "Deploy complete." -ForegroundColor Green
