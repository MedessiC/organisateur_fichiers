#!/usr/bin/env python3
# MEDETEST - Mini outil de pentesting web
# Auteur: Medessi Coovi

import argparse
import socket
import requests
import ssl
import subprocess
import concurrent.futures
import re
import json
from urllib.parse import urlparse
from datetime import datetime

class ColorOutput:
    """Classe pour ajouter des couleurs aux sorties console"""
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class PenScout:
    def __init__(self, target, output=None, threads=10, timeout=5):
        self.target = target
        self.output = output
        self.threads = threads
        self.timeout = timeout
        self.results = {
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": target,
            "vulnerabilities": [],
            "open_ports": [],
            "headers_analysis": {},
            "directory_findings": []
        }
        
        # Parsez l'URL pour extraire le domaine
        parsed_url = urlparse(target)
        self.domain = parsed_url.netloc
        if not self.domain:
            self.domain = self.target
        
        # Assurez-vous que la cible a un schéma
        if not parsed_url.scheme:
            self.target = f"http://{self.target}"
    
    def run_scan(self):
        """Exécute tous les modules de scan"""
        print(f"{ColorOutput.BOLD}{ColorOutput.BLUE}[*] Démarrage du scan PenScout sur {self.target}{ColorOutput.RESET}")
        
        # Exécution des modules
        self.check_ssl_cert()
        self.scan_common_ports()
        self.analyze_http_headers()
        self.check_common_vulnerabilities()
        self.fuzzing_directories()
        
        # Sauvegarde des résultats si demandé
        if self.output:
            self.save_results()
            
        print(f"{ColorOutput.BOLD}{ColorOutput.GREEN}[+] Scan terminé pour {self.target}{ColorOutput.RESET}")
        
    def check_ssl_cert(self):
        """Vérifier les informations du certificat SSL"""
        print(f"{ColorOutput.BOLD}[*] Vérification du certificat SSL...{ColorOutput.RESET}")
        
        parsed_url = urlparse(self.target)
        hostname = parsed_url.netloc
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Vérifier la date d'expiration
                    expires = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                    current_date = datetime.now()
                    days_left = (expires - current_date).days
                    
                    if days_left < 30:
                        print(f"{ColorOutput.YELLOW}[!] Le certificat SSL expire dans {days_left} jours{ColorOutput.RESET}")
                        self.results["vulnerabilities"].append({
                            "type": "ssl_expiration",
                            "severity": "medium",
                            "description": f"Le certificat SSL expire dans {days_left} jours"
                        })
                    else:
                        print(f"{ColorOutput.GREEN}[+] Certificat SSL valide (expire dans {days_left} jours){ColorOutput.RESET}")
                        
                    # Vérifier la version de TLS
                    tls_version = ssock.version()
                    if tls_version not in ['TLSv1.2', 'TLSv1.3']:
                        print(f"{ColorOutput.YELLOW}[!] Version TLS obsolète : {tls_version}{ColorOutput.RESET}")
                        self.results["vulnerabilities"].append({
                            "type": "weak_tls",
                            "severity": "high",
                            "description": f"Version TLS obsolète détectée : {tls_version}"
                        })
        except (socket.gaierror, ssl.SSLError, socket.timeout, ConnectionRefusedError) as e:
            print(f"{ColorOutput.RED}[-] Impossible de vérifier le certificat SSL: {str(e)}{ColorOutput.RESET}")
    
    def scan_port(self, port):
        """Scanner un port spécifique"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        try:
            result = sock.connect_ex((self.domain, port))
            if result == 0:
                try:
                    service = socket.getservbyport(port)
                except OSError:
                    service = "unknown"
                
                self.results["open_ports"].append({"port": port, "service": service})
                print(f"{ColorOutput.GREEN}[+] Port {port} ({service}) - Ouvert{ColorOutput.RESET}")
                return port, True
            return port, False
        except (socket.gaierror, socket.error, socket.timeout):
            return port, False
        finally:
            sock.close()
    
    def scan_common_ports(self):
        """Scanner les ports communs"""
        common_ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5900, 8080]
        print(f"{ColorOutput.BOLD}[*] Scan des ports communs sur {self.domain}...{ColorOutput.RESET}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            results = list(executor.map(self.scan_port, common_ports))
            
        open_ports = [port for port, is_open in results if is_open]
        
        if not open_ports:
            print(f"{ColorOutput.YELLOW}[!] Aucun port ouvert trouvé parmi les ports communs{ColorOutput.RESET}")
    
    def analyze_http_headers(self):
        """Analyser les en-têtes HTTP pour les problèmes de sécurité"""
        print(f"{ColorOutput.BOLD}[*] Analyse des en-têtes de sécurité HTTP...{ColorOutput.RESET}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.target, headers=headers, timeout=self.timeout, verify=False)
            
            security_headers = {
                'Strict-Transport-Security': False,
                'Content-Security-Policy': False,
                'X-Content-Type-Options': False,
                'X-Frame-Options': False,
                'X-XSS-Protection': False,
                'Referrer-Policy': False
            }
            
            for header in security_headers:
                if header in response.headers:
                    security_headers[header] = True
                    print(f"{ColorOutput.GREEN}[+] {header} est présent{ColorOutput.RESET}")
                else:
                    print(f"{ColorOutput.YELLOW}[!] {header} est manquant{ColorOutput.RESET}")
                    self.results["vulnerabilities"].append({
                        "type": "missing_security_header",
                        "severity": "medium",
                        "description": f"En-tête de sécurité manquant: {header}"
                    })
            
            self.results["headers_analysis"] = security_headers
            
            # Vérifier les cookies pour les attributs de sécurité
            if 'Set-Cookie' in response.headers:
                cookies = response.headers.get('Set-Cookie')
                if 'HttpOnly' not in cookies:
                    print(f"{ColorOutput.YELLOW}[!] Attribut HttpOnly manquant dans les cookies{ColorOutput.RESET}")
                    self.results["vulnerabilities"].append({
                        "type": "insecure_cookie",
                        "severity": "medium",
                        "description": "L'attribut HttpOnly est manquant dans les cookies"
                    })
                if 'Secure' not in cookies and self.target.startswith('https'):
                    print(f"{ColorOutput.YELLOW}[!] Attribut Secure manquant dans les cookies{ColorOutput.RESET}")
                    self.results["vulnerabilities"].append({
                        "type": "insecure_cookie",
                        "severity": "medium",
                        "description": "L'attribut Secure est manquant dans les cookies"
                    })
                
            # Informations sur le serveur
            server = response.headers.get('Server', '')
            if server:
                print(f"{ColorOutput.BLUE}[*] Serveur identifié: {server}{ColorOutput.RESET}")
                self.results["server_info"] = server
                
                # Vérifier si la version est divulguée
                if re.search(r'[0-9]', server):
                    print(f"{ColorOutput.YELLOW}[!] Version du serveur divulguée: {server}{ColorOutput.RESET}")
                    self.results["vulnerabilities"].append({
                        "type": "server_version_disclosure",
                        "severity": "low",
                        "description": f"La version du serveur est divulguée: {server}"
                    })
            
        except requests.exceptions.RequestException as e:
            print(f"{ColorOutput.RED}[-] Erreur lors de l'analyse des en-têtes: {str(e)}{ColorOutput.RESET}")
    
    def check_common_vulnerabilities(self):
        """Vérifier les vulnérabilités web courantes"""
        print(f"{ColorOutput.BOLD}[*] Vérification des vulnérabilités courantes...{ColorOutput.RESET}")
        
        # Liste des chemins potentiellement vulnérables à tester
        paths_to_check = [
            ("/robots.txt", "Fichier robots.txt accessible"),
            ("/.git/", "Répertoire Git exposé"),
            ("/.env", "Fichier .env exposé"),
            ("/backup/", "Répertoire de sauvegarde exposé"),
            ("/phpinfo.php", "Page phpinfo exposée"),
            ("/wp-login.php", "Site WordPress détecté"),
            ("/wp-json/", "API WordPress détectée"),
            ("/admin/", "Panneau d'administration potentiel"),
            ("/login/", "Page de connexion détectée")
        ]
        
        for path, description in paths_to_check:
            try:
                url = self.target.rstrip('/') + path
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=self.timeout, verify=False, allow_redirects=False)
                
                if response.status_code == 200:
                    print(f"{ColorOutput.YELLOW}[!] {description}: {url}{ColorOutput.RESET}")
                    self.results["vulnerabilities"].append({
                        "type": "information_disclosure",
                        "severity": "medium",
                        "description": description,
                        "url": url
                    })
            except requests.exceptions.RequestException:
                pass
        
        # Test simple d'injection SQL
        try:
            payload = "' OR '1'='1"
            for param in ['id', 'user', 'page', 'search']:
                url = f"{self.target}?{param}={payload}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
                
                if "error" in response.text.lower() and "sql" in response.text.lower():
                    print(f"{ColorOutput.RED}[!] Potentielle vulnérabilité d'injection SQL détectée: {url}{ColorOutput.RESET}")
                    self.results["vulnerabilities"].append({
                        "type": "sql_injection",
                        "severity": "high",
                        "description": f"Potentielle vulnérabilité d'injection SQL sur le paramètre '{param}'",
                        "url": url
                    })
        except requests.exceptions.RequestException:
            pass
        
        # Test simple XSS
        try:
            xss_payload = "<script>alert(1)</script>"
            for param in ['search', 'q', 'query', 'id']:
                url = f"{self.target}?{param}={xss_payload}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
                
                if xss_payload in response.text:
                    print(f"{ColorOutput.RED}[!] Potentielle vulnérabilité XSS détectée: {url}{ColorOutput.RESET}")
                    self.results["vulnerabilities"].append({
                        "type": "xss",
                        "severity": "high",
                        "description": f"Potentielle vulnérabilité XSS sur le paramètre '{param}'",
                        "url": url
                    })
        except requests.exceptions.RequestException:
            pass
    
    def fuzzing_directories(self):
        """Fuzzing de répertoires et fichiers communs"""
        print(f"{ColorOutput.BOLD}[*] Fuzzing de chemins communs...{ColorOutput.RESET}")
        
        common_paths = [
            "/admin", "/login", "/wp-admin", "/phpmyadmin", "/dashboard", 
            "/backup", "/config", "/dev", "/test", "/api", "/api/v1", 
            "/docs", "/upload", "/uploads", "/files", "/tmp", "/temp"
        ]
        
        def check_path(path):
            url = self.target.rstrip('/') + path
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=self.timeout, verify=False, allow_redirects=False)
                
                if response.status_code in [200, 302, 401, 403]:
                    if response.status_code == 200:
                        status = f"{ColorOutput.GREEN}200{ColorOutput.RESET}"
                    elif response.status_code == 302:
                        status = f"{ColorOutput.BLUE}302{ColorOutput.RESET}"
                    elif response.status_code in [401, 403]:
                        status = f"{ColorOutput.YELLOW}{response.status_code}{ColorOutput.RESET}"
                    
                    print(f"[+] {status} - {url}")
                    return {
                        "path": path,
                        "url": url,
                        "status_code": response.status_code
                    }
                return None
            except requests.exceptions.RequestException:
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            results = list(executor.map(check_path, common_paths))
            
        # Filtrer les résultats None
        findings = [result for result in results if result]
        self.results["directory_findings"] = findings
        
        if not findings:
            print(f"{ColorOutput.YELLOW}[!] Aucun chemin intéressant trouvé{ColorOutput.RESET}")
    
    def save_results(self):
        """Sauvegarder les résultats dans un fichier"""
        try:
            with open(self.output, 'w') as f:
                json.dump(self.results, f, indent=4)
            print(f"{ColorOutput.GREEN}[+] Résultats sauvegardés dans {self.output}{ColorOutput.RESET}")
        except Exception as e:
            print(f"{ColorOutput.RED}[-] Erreur lors de la sauvegarde des résultats: {str(e)}{ColorOutput.RESET}")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='MEDETEST - Mini outil de pentesting web')
    parser.add_argument('-t', '--target', required=True, help='URL ou domaine cible')
    parser.add_argument('-o', '--output', help='Fichier de sortie pour les résultats (JSON)')
    parser.add_argument('--threads', type=int, default=10, help='Nombre de threads pour les scans parallèles')
    parser.add_argument('--timeout', type=int, default=5, help='Timeout pour les requêtes (secondes)')
    
    args = parser.parse_args()

    
    print(f"""
{ColorOutput.BOLD}{ColorOutput.PURPLE}

   \  |  ____|  __ \   ____| __ __|  ____|   ___| __ __| 
  |\/ |  __|    |   |  __|      |    __|   \___ \    |   
  |   |  |      |   |  |        |    |           |   |   
 _|  _| _____| ____/  _____|   _|   _____| _____/   _|   
                                                         

{ColorOutput.RESET}Mini outil de pentesting web
    """)
    
    scanner = PenScout(args.target, args.output, args.threads, args.timeout)
    scanner.run_scan()

if __name__ == "__main__":
    # Désactiver les avertissements liés aux certificats SSL non vérifiés
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main()