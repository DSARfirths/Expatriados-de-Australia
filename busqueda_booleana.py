import time, re, csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException

BASE_URL = (
    'https://www.linkedin.com/search/results/people/'
    '?geoUrn=["117523689","103291313"]'
    '&keywords=Australia'
    '&origin=FACETED_SEARCH'
)

# ----------------------------------------------------------------
# 1) Función para extraer email y teléfono de un perfil de LinkedIn
# ----------------------------------------------------------------
def buscar_perfiles_linkedin(email, pwd, pool_size = 50):
    """Recoge hasta pool_size URLs con /in/, sin extraer contacto."""
    driver = uc.Chrome(headless=False)
    wait   = WebDriverWait(driver, 10)

    # 1. Login
    driver.get('https://www.linkedin.com/login')
    wait.until(EC.element_to_be_clickable((By.ID, 'username'))).send_keys(email)
    driver.find_element(By.ID, 'password').send_keys(pwd)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    wait.until(EC.url_contains('/feed'))
    time.sleep(2)

    urls = []
    # 2. Paginación
    for page in range(1, 6): # probamos hasta 5 páginas => pool_size ≈ 50
        driver.get(f'{BASE_URL}&page={page}')
        try:
            # Espera a que cargue al menos un enlace de perfil
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/in/"]')))
        except TimeoutException:
            print(f'[-] Timeout en la página {page}, no hay resultados.')
            continue
        # 3. Damos un respiro antes de raspar todos los <a>
        time.sleep(2)

        # 4. Escanear TODOS los <a> y filtrar los /in/
        for a in driver.find_elements(By.TAG_NAME, 'a'):
            href = a.get_attribute('href') or ''
            if '/in/' in href:
                clean = href.split('?')[0]      # ✂️ elimina todo desde '?'
                if re.match(r'^https://www\.linkedin\.com/in/[^/]+/?$', clean):
                    if clean not in urls:
                        urls.append(clean)
                        print(f'[+] Añadida URL limpia: {clean}')
                        if len(urls) >= pool_size:
                            print(f'[✔] Pool de {pool_size} URLs listo.')
                            break   # rompe el for de <a>
        # Si rompimos el for interno, sale al for de páginas
        if len(urls) >= pool_size:
            break
    return driver, wait, urls

# ----------------------------------------------------------------
# 2) Función para extraer email y teléfono de un perfil de LinkedIn
# ----------------------------------------------------------------
def obtener_contacto(driver, wait):
    email = telefono = ''
    try:
        btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@href,'/detail/contact-info')]")
        ))
        btn.click()
        wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'section.pv-contact-info')
        ))

        # 🔍 find_elements en plural
        email_elems = driver.find_elements(
            By.XPATH, "//a[starts-with(@href,'mailto:')]"
        )
        if email_elems:
            email = email_elems[0].get_attribute('href').split('mailto:')[-1]

        phones = driver.find_elements(By.CSS_SELECTOR, 'section.ci-phone li')
        if phones:
            telefono = phones[0].text.strip()

    except (TimeoutException, NoSuchElementException):
        # perfil privado o ruta incorrecta: devolvemos ('','')
        pass

    return email, telefono

def main():
    EMAIL = 'Aqui_coloca_tu_correo@gmail.com'
    PWD   = 'password'

# -----------------------------------------------------------
# 3) Código principal: recorre los perfiles y pisa un CSV
# -----------------------------------------------------------
 # 1) Consigue un pool grande de URLs
    driver, wait, pool = buscar_perfiles_linkedin(EMAIL, PWD, pool_size=50)

    # 2) Abre cada URL y construye tu CSV hasta 20 filas válidas
    with open('expat_au_hk.csv','w',newline='',encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Nombre','Email','Teléfono','LinkedIn','Justificación','País'])
        count = 0

        for url in pool:
            if count >= 20: break
            driver.get(url); time.sleep(1)

            # 2.A Detecta join-page y salta
            try:
                h1 = driver.find_element(By.TAG_NAME,'h1').text
            except NoSuchElementException:
                continue
            if 'LinkedIn' in h1 or 'Únete' in h1:
                continue

            # 2.B Nombre real
            nombre = h1.strip()

            # 2.C Contacto
            email, telefono = obtener_contacto(driver, wait)

            # 2.D Solo guardamos si hay **algún** dato de contacto
            if not email and not telefono:
                print(f'(!) Sin contacto en {url}, pero lo guardo para testear.')

            # 2.E Justificación
            justif = 'Origen Australia (+experiencia/edu) y residencia HK (geoUrn)'

            writer.writerow([nombre, email, telefono, url, justif, 'Hong Kong'])
            print(f'[✔] {nombre} — {email} — {telefono}')
            count += 1

    # 3) Cierre limpio
    try:
        driver.quit()
    except OSError:
        pass

if __name__ == '__main__':
    main()