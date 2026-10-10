import { test, expect, type Page } from "@playwright/test";
async function layout(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
}
async function fillProject(page: Page) {
  await page.getByRole("button", { name: "Commencer →", exact: true }).click();
  await page
    .getByRole("button", { name: "Remplir le formulaire", exact: true })
    .click();
  await page.getByLabel("Niveau de classe").fill("5e");
  await page.getByLabel("Thème pédagogique").selectOption("patrimoine");
  await page.getByLabel("Nombre d’élèves").fill("20");
  await page.getByLabel("Nombre d’accompagnateurs").fill("2");
  await page.getByLabel("Date précise").fill("2026-11-15");
  await page.getByLabel("Lieu réel de départ").fill("Collège de Toulouse");
  await page.getByLabel("Gare de départ").fill("Toulouse");
  await layout(page);
  await page.getByRole("button", { name: "Continuer →", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Avez-vous déjà une destination en tête ?",
    }),
  ).toBeVisible();
}
test("projet connu, aller/retour, dossier et retour d’expérience", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.screenshot({
    path: `/tmp/lio-home-${info.project.name}.png`,
    fullPage: true,
  });
  await fillProject(page);
  await page.getByRole("button", { name: /^Oui/ }).click();
  await page.getByLabel("Gare ou ville de destination").fill("Carcassonne");
  await page.getByRole("button", { name: "Continuer →", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Attractions autour de Carcassonne" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Sciences", exact: true }),
  ).toHaveCount(0);
  await page
    .locator(".destination-card")
    .filter({ hasText: "Cité de Carcassonne" })
    .locator(".visit-select")
    .click();
  await page
    .getByRole("button", { name: "Voir les trains pour cette destination" })
    .click();
  await expect(page.getByLabel("Arrivée")).toHaveValue("Carcassonne");
  await page
    .getByRole("button", { name: "Rechercher les trains", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Aucune source");
  await page.getByLabel("Consulter la démonstration").check();
  await page
    .getByRole("button", { name: "Rechercher les trains", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Trains disponibles pour Carcassonne" }),
  ).toBeVisible();
  await layout(page);
  await page
    .getByRole("button", { name: "Sélectionner", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: /Retour ·/ }).click();
  await page
    .getByRole("button", { name: "Sélectionner", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Continuer →", exact: true }).click();
  await expect(
    page.getByText("Récapitulatif de votre projet", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("20 élèves + 2 accompagnateurs (22 personnes)", {
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: `/tmp/lio-summary-${info.project.name}.png`,
    fullPage: true,
  });
  await layout(page);
  await page.getByRole("button", { name: "Continuer →", exact: true }).click();
  await page.getByLabel("Nom *", { exact: true }).fill("Test Enseignant");
  await page.getByLabel("Établissement scolaire").fill("Collège Test");
  await page.getByLabel("Email *", { exact: true }).fill("test@example.fr");
  await page.getByLabel("Je comprends").check();
  await page
    .getByRole("button", { name: "Envoyer ma demande de pré-réservation" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Votre dossier est en attente" }),
  ).toBeVisible();
  await expect(page.locator(".reference")).toContainText("LIO-");
  await page.getByRole("button", { name: "Partager un retour" }).click();
  await page.getByLabel("Votre commentaire").fill("Test de parcours complet.");
  await page.getByRole("button", { name: "Enregistrer mon retour" }).click();
  await expect(
    page.getByRole("heading", { name: "Merci pour votre retour !" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("destination inconnue, filtres et détails réels", async ({ page }) => {
  await page.goto("/");
  await fillProject(page);
  await page.getByRole("button", { name: "Continuer →", exact: true }).click();
  await expect(page.locator(".destination-card").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Histoire et patrimoine", exact: true })
    .click();
  await expect(page.locator(".destination-card").first()).toBeVisible();
  await layout(page);
  await page.locator(".destination-card .visit-select").first().click();
  await expect(page.getByText(/km à vol d’oiseau/).first()).toBeVisible();
  await expect(
    page.getByText(/Catalogue d’attractions · Mis à jour/),
  ).toBeVisible();
  await layout(page);
  await page
    .getByRole("button", { name: "Voir les trains pour cette destination" })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Recherchez les trains pour votre destination",
    }),
  ).toBeVisible();
});
test("chat, clarification, validation de l’effectif et brouillon", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Commencer →", exact: true }).click();
  await page.getByRole("button", { name: "Ouvrir le chat" }).click();
  await page
    .getByLabel("Votre message")
    .fill("Sortie patrimoine pour 25 élèves.");
  await page.getByRole("button", { name: "Envoyer →", exact: true }).click();
  await expect(
    page.getByText(/De quelle ville ou établissement/),
  ).toBeVisible();
  await page
    .getByLabel("Votre message")
    .fill("Au départ de Toulouse le 2026-11-15 avec 3 accompagnateurs.");
  await page.getByRole("button", { name: "Envoyer →", exact: true }).click();
  await expect(
    page.getByText("25 élèves · 3 accompagnateurs", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Vérifier et continuer" }).click();
  await expect(page.getByLabel("Gare de départ")).toHaveValue("Toulouse");
  await page.getByLabel("Nombre d’élèves").fill("50");
  await expect(page.getByRole("alert")).toContainText("53 voyageurs");
  await expect(
    page.getByRole("button", { name: "Continuer →", exact: true }),
  ).toBeDisabled();
  await layout(page);
  await page.reload();
  await expect(page.getByLabel("Gare de départ")).toHaveValue("Toulouse");
});

test("le lien suggestions et son rechargement interrogent l’API", async ({
  page,
}) => {
  const files: string[] = [];
  page.on("request", (request) => {
    if (/\.(csv|xlsx)(?:\?|$)/i.test(request.url())) files.push(request.url());
  });
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/destinations/search") &&
      response.request().method() === "POST",
  );
  await page.goto("/#suggestions");
  await expect(page.locator(".destination-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Sciences", exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const result = await response.json();
  await expect(page.locator(".destination-card")).toHaveCount(
    result.destinations.length,
  );
  await expect(page.locator(".destination-card").first()).toContainText(
    result.destinations[0].name,
  );
  const reloadResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/destinations/search") &&
      response.status() === 200,
  );
  await page.reload();
  await reloadResponse;
  await expect(page.locator(".destination-card")).toHaveCount(
    result.destinations.length,
  );
  expect(files).toEqual([]);
  await expect(page.locator("main")).not.toContainText(
    /\.xlsx|\.csv|classeur/i,
  );
});

test("une panne de l’API n’affiche aucun lieu de secours et permet de réessayer", async ({
  page,
}) => {
  await page.route("**/api/destinations/search", (route) =>
    route.abort("failed"),
  );
  await page.goto("/#suggestions");
  await page.getByRole("button", { name: "Sciences", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Impossible de charger les lieux",
  );
  await expect(page.locator(".destination-card")).toHaveCount(0);
  await page.unroute("**/api/destinations/search");
  await page.getByRole("button", { name: "Réessayer", exact: true }).click();
  await expect(page.locator(".destination-card").first()).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("chaque attraction affiche son score, son argumentaire et le trajet piéton", async ({
  page,
}, info) => {
  await page.goto("/#suggestions");
  await page
    .getByRole("button", { name: "Histoire et patrimoine", exact: true })
    .click();
  const card = page.locator(".destination-card").filter({
    has: page.getByRole("button", {
      name: "Voir le lieu : Cité de Carcassonne",
      exact: true,
    }),
  });
  await expect(
    card.getByText("50/100 · Adéquation pédagogique", { exact: true }),
  ).toBeVisible();
  await expect(
    card.getByRole("heading", { name: "Intérêt pédagogique", exact: true }),
  ).toBeVisible();
  await expect(card.locator(".regulatory-argument p")).toContainText(
    "circulaire du 16 juillet 2024",
  );
  await expect(card.getByText("40 min à pied", { exact: true })).toBeVisible();
  await expect(
    card.getByRole("link", { name: "Circulaire du 16 juillet 2024" }),
  ).toHaveAttribute(
    "href",
    "https://www.education.gouv.fr/bo/2024/Hebdo30/MENE2407159C",
  );
  await card.getByText("Comprendre le score", { exact: true }).click();
  await expect(
    card.getByText("Disciplines : critère non renseigné", { exact: true }),
  ).toBeVisible();
  const assessmentBox = await card.locator(".visit-assessment").boundingBox();
  expect(assessmentBox?.width).toBeGreaterThan(250);
  await card.screenshot({
    path: `/tmp/lio-visit-assessment-${info.project.name}.png`,
  });
  await card
    .getByRole("button", {
      name: "Voir le lieu : Cité de Carcassonne",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Cité de Carcassonne", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("40 min à pied", { exact: true })).toBeVisible();
  await layout(page);
});

test("une panne du calcul piéton garde le score et permet de réessayer", async ({
  page,
}) => {
  await page.route("**/api/destinations/cite-carcassonne/walking", (route) =>
    route.abort("failed"),
  );
  await page.goto("/#suggestions");
  await page
    .getByRole("button", { name: "Histoire et patrimoine", exact: true })
    .click();
  const card = page.locator(".destination-card").filter({
    has: page.getByRole("button", {
      name: "Voir le lieu : Cité de Carcassonne",
      exact: true,
    }),
  });
  await expect(
    card.getByText("Temps de marche indisponible.", { exact: true }),
  ).toBeVisible();
  await expect(
    card.getByText("50/100 · Adéquation pédagogique", { exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/destinations/cite-carcassonne/walking");
  await card
    .getByRole("button", { name: "Réessayer le calcul à pied" })
    .click();
  await expect(card.getByText("40 min à pied", { exact: true })).toBeVisible();
});
