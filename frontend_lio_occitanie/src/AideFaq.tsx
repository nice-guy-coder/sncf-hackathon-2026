import { useState, useMemo } from "react";

interface QAItem {
  id: string;
  question: string;
  answer: React.ReactNode;
  keywords?: string;
  defaultOpen?: boolean;
}

interface Category {
  id: string;
  num: number;
  title: string;
  items: QAItem[];
}

const FAQ_DATA: Category[] = [
  {
    id: "cat-1",
    num: 1,
    title: "Découvrir la plateforme",
    items: [
      {
        id: "cat-1-1",
        defaultOpen: true,
        question: "Qu'est-ce que le Copilote de sorties scolaires ?",
        answer: (
          <>
            <p>
              Le Copilote de sorties scolaires est un outil conçu pour aider les
              enseignants à organiser des sorties pédagogiques en Occitanie en
              privilégiant les trains liO.
            </p>
            <p>
              Il vous accompagne dans la préparation de votre projet, la
              recherche de destinations, l'analyse des possibilités de transport
              et la demande de pré-réservation.
            </p>
            <p>
              Son objectif est de vous aider à organiser une sortie pertinente,
              réalisable et plus sereine.
            </p>
          </>
        ),
      },
      {
        id: "cat-1-2",
        question: "Comment fonctionne la plateforme ?",
        answer: (
          <>
            <p>Le parcours se déroule en plusieurs étapes :</p>
            <ul>
              <li>Vous décrivez votre projet pédagogique.</li>
              <li>La plateforme analyse votre besoin.</li>
              <li>
                Elle vous propose des destinations adaptées lorsque les données
                disponibles le permettent.
              </li>
              <li>Vous choisissez une destination.</li>
              <li>
                Le système recherche les possibilités de transport, si une
                source ferroviaire actualisée est disponible.
              </li>
              <li>
                Vous consultez les informations, les points de vigilance et les
                alternatives éventuelles.
              </li>
              <li>Vous pouvez transmettre une demande de pré-réservation.</li>
            </ul>
            <p>
              Les informations disponibles et les éventuelles limitations sont
              indiquées au cours du parcours.
            </p>
          </>
        ),
      },
    ],
  },
  {
    id: "cat-2",
    num: 2,
    title: "Préparer mon projet pédagogique",
    items: [
      {
        id: "cat-2-1",
        question: "Quelles informations dois-je fournir pour commencer ?",
        answer: (
          <>
            <p>
              Pour commencer, décrivez votre projet pédagogique en précisant,
              autant que possible :
            </p>
            <ul>
              <li>Le niveau de votre classe.</li>
              <li>Le thème ou l'objectif pédagogique.</li>
              <li>Le nombre d'élèves.</li>
              <li>Le nombre d'accompagnateurs.</li>
              <li>La date souhaitée pour la sortie.</li>
              <li>Les horaires ou contraintes horaires souhaités.</li>
              <li>La gare de départ.</li>
            </ul>
            <p>
              Vous pouvez décrire votre besoin avec vos propres mots. La
              plateforme vous demandera des précisions si certaines informations
              indispensables sont manquantes ou ambiguës.
            </p>
          </>
        ),
      },
      {
        id: "cat-2-2",
        question: "Dois-je déjà connaître ma destination ?",
        answer: (
          <>
            <p>
              Non. Vous pouvez commencer par décrire votre projet pédagogique,
              sans avoir choisi de destination.
            </p>
            <p>
              La plateforme peut vous aider à identifier des destinations
              pertinentes en fonction du thème de votre sortie et des
              informations disponibles.
            </p>
            <p>
              Si vous connaissez déjà le lieu que vous souhaitez visiter, vous
              pouvez également le préciser.
            </p>
            <p>
              Les suggestions dépendent des données effectivement disponibles
              dans le système.
            </p>
          </>
        ),
      },
    ],
  },
  {
    id: "cat-3",
    num: 3,
    title: "Choisir une destination",
    items: [
      {
        id: "cat-3-1",
        question: "Comment les destinations sont-elles recommandées ?",
        answer: (
          <>
            <p>Les recommandations prennent notamment en compte :</p>
            <ul>
              <li>La pertinence pédagogique du lieu.</li>
              <li>
                Son intérêt culturel, historique, scientifique ou
                environnemental.
              </li>
              <li>Les activités ou visites envisageables.</li>
              <li>La compatibilité avec votre projet.</li>
              <li>
                Les possibilités d'accès en train liO, lorsque les données
                nécessaires sont disponibles.
              </li>
            </ul>
            <p>
              L'objectif est de vous aider à comparer plusieurs possibilités
              avant de choisir.
            </p>
            <p>
              Une recommandation ne constitue toutefois pas une garantie que
              l'ensemble du voyage sera réalisable.
            </p>
          </>
        ),
      },
      {
        id: "cat-3-2",
        question: "Puis-je comparer plusieurs destinations ?",
        answer: (
          <>
            <p>
              Oui. Le parcours prévu permet de comparer plusieurs propositions
              selon différents critères :
            </p>
            <ul>
              <li>Intérêt pédagogique.</li>
              <li>Simplicité du trajet.</li>
              <li>Accessibilité.</li>
              <li>Fiabilité des informations disponibles.</li>
              <li>Disponibilité, lorsqu'elle peut être vérifiée.</li>
              <li>
                Retours d'expérience des enseignants, lorsqu'ils existent.
              </li>
            </ul>
            <p>
              Cette comparaison doit vous aider à choisir la proposition la plus
              adaptée à votre classe.
            </p>
          </>
        ),
      },
    ],
  },
  {
    id: "cat-4",
    num: 4,
    title: "Comprendre les trajets en train liO",
    items: [
      {
        id: "cat-4-1",
        question: "Comment savoir si un train est adapté à mon groupe ?",
        answer: (
          <>
            <p>Le système doit vérifier plusieurs éléments, notamment :</p>
            <ul>
              <li>Si le train est autorisé aux groupes scolaires.</li>
              <li>
                Si les horaires aller et retour sont compatibles avec votre
                sortie.
              </li>
              <li>Si la capacité du train permet d'accueillir votre groupe.</li>
              <li>
                Si les éventuelles correspondances sont compatibles avec votre
                programme.
              </li>
              <li>
                Si le temps de déplacement laisse une marge suffisante avant la
                visite.
              </li>
              <li>
                Si les options déjà positionnées par d'autres groupes sont
                prises en compte.
              </li>
            </ul>
            <p>
              La capacité et la disponibilité doivent être vérifiées à partir
              des données appropriées. Si une information ne peut pas être
              confirmée, elle ne doit pas être présentée comme acquise.
            </p>
          </>
        ),
      },
      {
        id: "cat-4-2",
        question: "Comment savoir si le site est accessible depuis la gare ?",
        answer: (
          <>
            <p>
              La plateforme doit examiner les possibilités de déplacement entre
              la gare d'arrivée et le site à visiter.
            </p>
            <p>
              L'objectif privilégié est un trajet de{" "}
              <b style={{ color: "var(--ink)" }}>20 minutes maximum à pied</b>,
              ou un accès possible par le réseau de transport urbain dans un
              délai compatible avec la sortie.
            </p>
            <p>
              Le temps nécessaire à un groupe scolaire doit être pris en compte.
            </p>
            <p>
              Si l'accès est trop long ou si les informations sont
              insuffisantes, un point de vigilance doit être signalé afin de vous
              aider à évaluer la faisabilité du déplacement.
            </p>
          </>
        ),
      },
    ],
  },
  {
    id: "cat-5",
    num: 5,
    title: "Comprendre la fiabilité des recommandations",
    items: [
      {
        id: "cat-5-1",
        question: "Que signifie l'indicateur de confiance ?",
        answer: (
          <>
            <p>
              L'indicateur de confiance vise à vous aider à comprendre la
              fiabilité et la pertinence d'une proposition.
            </p>
            <p>Il peut notamment prendre en compte :</p>
            <ul>
              <li>La capacité et l'adaptation du transport au groupe.</li>
              <li>La régularité historique du train.</li>
              <li>Les risques de suppression observés.</li>
              <li>La faisabilité des horaires.</li>
              <li>L'accessibilité entre la gare et le site culturel.</li>
              <li>La pertinence pédagogique.</li>
              <li>Les retours d'expérience disponibles.</li>
            </ul>
            <p>
              L'indicateur doit être accompagné d'explications permettant de
              comprendre les éléments qui influencent l'évaluation.
            </p>
            <span className="note">
              ⚠ Un indicateur de confiance ne garantit ni la circulation future
              d'un train ni la confirmation d'une réservation.
            </span>
          </>
        ),
      },
      {
        id: "cat-5-2",
        question:
          "Pourquoi certaines informations sont-elles indiquées comme indisponibles ou non vérifiables ?",
        answer: (
          <>
            <p>
              Certaines informations nécessitent des données actualisées ou des
              sources spécifiques.
            </p>
            <p>
              Par exemple, les horaires réels, la disponibilité d'un train ou la
              durée exacte d'un trajet peuvent ne pas être vérifiables si la
              source nécessaire n'est pas connectée au système.
            </p>
            <p>
              Dans ce cas, la plateforme doit signaler clairement la limitation.
              Elle ne doit pas inventer une information ni présenter une
              estimation comme un fait confirmé.
            </p>
            <p>
              Vous pouvez alors examiner les informations disponibles ou
              envisager une autre proposition.
            </p>
          </>
        ),
      },
    ],
  },
  {
    id: "cat-6",
    num: 6,
    title: "Effectuer une pré-réservation",
    items: [
      {
        id: "cat-6-1",
        question: "Comment effectuer une demande de pré-réservation ?",
        answer: (
          <>
            <p>
              Après avoir choisi une proposition, vous pouvez transmettre une
              demande de pré-réservation.
            </p>
            <p>
              Selon le parcours prévu, le système peut vous demander les
              informations nécessaires au traitement de votre demande,
              notamment :
            </p>
            <ul>
              <li>Votre nom.</li>
              <li>Le nom de votre établissement.</li>
              <li>Votre adresse électronique.</li>
              <li>
                Les informations relatives à la sortie et à l'itinéraire choisi,
                si celui-ci est disponible.
              </li>
            </ul>
            <p>
              Une référence de dossier peut être générée afin de faciliter le
              suivi de votre demande.
            </p>
            <p>
              Les modalités définitives dépendent des fonctionnalités
              effectivement disponibles dans la plateforme.
            </p>
          </>
        ),
      },
      {
        id: "cat-6-2",
        question:
          "Ma demande de pré-réservation garantit-elle que mon voyage est confirmé ?",
        answer: (
          <>
            <p>
              <b style={{ color: "var(--ink)" }}>Non.</b> Une demande de
              pré-réservation ne constitue pas une réservation confirmée.
            </p>
            <p>
              Après l'envoi de votre demande, son statut reste en attente tant
              qu'une confirmation officielle n'a pas été reçue.
            </p>
            <p>La plateforme doit distinguer clairement les étapes suivantes :</p>
            <ul>
              <li>Proposition.</li>
              <li>Option éventuelle.</li>
              <li>Demande de pré-réservation.</li>
              <li>Confirmation officielle.</li>
            </ul>
            <span className="note">
              ⚠ Ne considérez pas votre voyage comme confirmé avant d'avoir reçu
              la confirmation correspondante.
            </span>
          </>
        ),
      },
      {
        id: "cat-6-3",
        question:
          "Que se passe-t-il si mon groupe est trop nombreux ou si le train n'est pas adapté ?",
        answer: (
          <>
            <p>
              Si une proposition ne répond pas aux contraintes identifiées, la
              plateforme doit vous expliquer le problème rencontré. Par exemple :
            </p>
            <ul>
              <li>La capacité disponible semble insuffisante pour votre groupe.</li>
              <li>
                Le trajet retour ne correspond pas aux horaires de votre
                activité.
              </li>
              <li>
                L'accès entre la gare et le site est trop contraignant.
              </li>
              <li>Une information indispensable ne peut pas être vérifiée.</li>
            </ul>
            <p>
              Lorsque cela est possible, le système peut vous proposer une autre
              destination ou une solution de transport alternative compatible
              avec les règles du projet.
            </p>
            <p>
              L'objectif est de vous aider à prendre une décision éclairée, et
              non de vous présenter une proposition incertaine comme une solution
              garantie.
            </p>
          </>
        ),
      },
    ],
  },
  {
    id: "cat-7",
    num: 7,
    title: "Retours d'expérience",
    items: [
      {
        id: "cat-7-1",
        question: "Puis-je donner mon avis après la sortie scolaire ?",
        answer: (
          <>
            <p>
              Le projet prévoit un retour d'expérience après le voyage. Vous
              pourrez notamment être invité à évaluer :
            </p>
            <ul>
              <li>Votre satisfaction globale.</li>
              <li>La facilité de préparation de la sortie.</li>
              <li>La clarté des informations fournies.</li>
              <li>L'adaptation du transport à votre groupe.</li>
              <li>Les horaires et les correspondances.</li>
              <li>L'accessibilité entre la gare et le site.</li>
              <li>Votre niveau de confiance dans l'expérience.</li>
            </ul>
            <p>
              Ces retours pourront contribuer à améliorer progressivement les
              recommandations et à faire ressortir les expériences
              particulièrement appréciées des enseignants.
            </p>
            <p>
              La disponibilité de cette fonctionnalité dépendra de son
              implémentation dans la plateforme.
            </p>
          </>
        ),
      },
    ],
  },
];

interface AideFaqProps {
  onStartProject?: () => void;
}

export function AideFaq({ onStartProject }: AideFaqProps) {
  const [search, setSearch] = useState("");
  const [activeCat, setActiveCat] = useState("cat-1");

  const query = search.trim().toLowerCase();

  // Helper text extraction for search matching
  const filteredCategories = useMemo(() => {
    if (!query) {
      return FAQ_DATA;
    }

    return FAQ_DATA.map((cat) => {
      const filteredItems = cat.items.filter((item) => {
        const qMatch = item.question.toLowerCase().includes(query);
        const catMatch = cat.title.toLowerCase().includes(query);
        // Also check raw string content of answer if needed
        const answerText = item.id.toLowerCase();
        return qMatch || catMatch || answerText.includes(query);
      });

      return {
        ...cat,
        items: filteredItems,
      };
    }).filter((cat) => cat.items.length > 0);
  }, [query]);

  const scrollToCat = (catId: string) => {
    setActiveCat(catId);
    const el = document.getElementById(catId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="aide-faq-container">
      <span className="eyebrow">Aide</span>
      <h1 className="h1">Aide — Questions fréquentes</h1>

      <div className="intro">
        <p>
          Vous avez des questions sur l'organisation de votre sortie scolaire en
          train liO ?
        </p>
        <p>
          Retrouvez ici les réponses aux questions les plus fréquentes pour
          préparer votre projet pédagogique, choisir une destination,
          comprendre les possibilités de transport et effectuer une demande de
          pré-réservation.
        </p>
        <p>
          <b>Choisissez une catégorie pour consulter les réponses.</b>
        </p>
      </div>

      <div className="search">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher une question (ex. pré-réservation, destination, train…)"
          aria-label="Rechercher dans la foire aux questions"
        />
      </div>

      <div className="cat-row" role="tablist" aria-label="Catégories d'aide">
        {FAQ_DATA.map((cat) => (
          <button
            type="button"
            key={cat.id}
            role="tab"
            aria-selected={activeCat === cat.id}
            className={`cat-pill ${activeCat === cat.id ? "on" : ""}`}
            onClick={() => scrollToCat(cat.id)}
          >
            {cat.num}. {cat.title}
          </button>
        ))}
      </div>

      {filteredCategories.length === 0 ? (
        <p className="muted" style={{ padding: "32px 0", fontStyle: "italic" }}>
          Aucune question trouvée pour « {search} ».
        </p>
      ) : (
        filteredCategories.map((cat) => (
          <section className="category" id={cat.id} key={cat.id}>
            <div className="category-head">
              <span className="category-num">{cat.num}</span>
              <h2>{cat.title}</h2>
            </div>
            <div className="accordion">
              {cat.items.map((item) => (
                <details
                  className="qa"
                  key={item.id}
                  open={Boolean(query) || item.defaultOpen}
                >
                  <summary>
                    <span className="plus" aria-hidden="true">
                      +
                    </span>
                    {item.question}
                  </summary>
                  <div className="answer">{item.answer}</div>
                </details>
              ))}
            </div>
          </section>
        ))
      )}

      {onStartProject && (
        <div className="row-btns" style={{ marginTop: "48px" }}>
          <button
            type="button"
            className="btn"
            onClick={onStartProject}
          >
            Commencer mon projet →
          </button>
        </div>
      )}
    </div>
  );
}
