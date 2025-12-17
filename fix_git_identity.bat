@echo off
echo Setting git config...
git config user.name "Bastiansilabantio"
git config user.email "bastian.122450130@student.itera.ac.id"

echo Verifying config...
git config user.name
git config user.email

echo Amending last commit again...
git commit --amend --reset-author --no-edit

echo Force pushing to remote...
git push --force

echo Success!
