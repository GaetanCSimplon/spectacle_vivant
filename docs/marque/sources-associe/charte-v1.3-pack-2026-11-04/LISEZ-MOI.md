# BÒRD PRO · pack Affinity (04.11.2026)

## Contenu
- `1_planche_controle/` : planche SVG de tous les logos, un calque par couleur. À ouvrir dans Affinity pour vérifier.
- `2_charte_pdf/` : la charte (14 pages A4 paysage) en PDF, pour référence.
- `3_svg_sources/` : un SVG par logo, icône, gimic et RADAR (calques : nuit, corail, ocean, pale, blanc).
- `4_exports_web_provisoires/` : PNG (transparents) et SVG générés depuis ces tracés. PROVISOIRES : à remplacer par vos exports Affinity une fois vérifiés.
- `5_png_originaux/` : les PNG de votre LOGO_3 (référence de comparaison).
- `EXPORTS_a_produire.csv` : liste des fichiers, tailles et usages pour le web designer.
- `BRD_PRO_design-tokens.css` : jetons v1.3 (les noms de fichiers y correspondent).

## Ce qui est fait automatiquement (fait établi)
Les PNG ont été tracés automatiquement (potrace) en calques de couleurs plates. Les gimics sont tracés depuis le « b » de la tuile. Rien n’est redessiné ni corrigé.

## Ce qui reste à faire dans Affinity (par vous)
1. Ouvrir `BORD_PRO_planche_controle_logos.svg`, superposer chaque tracé sur le PNG original (`5_png_originaux`) et contrôler les contours.
2. Corriger dans le tracé : filets visibles entre R et D, B et Ò soudés, accent anguleux, liseré bleu clair sur la tuile nuit. Ces défauts viennent du dessin d’origine.
3. Lisser les courbes (le tracé automatique crée beaucoup de nœuds), vérifier l’épaisseur du contour des tuiles.
4. Exporter les SVG et les PNG listés dans `EXPORTS_a_produire.csv`, fond transparent, et cocher la dernière colonne.
5. Remplacer le contenu de `4_exports_web_provisoires/` par vos exports.

## Notes
- Le texte « BÒRD PRO » est tracé en courbes : aucune police à installer.
- Les polices de la planche (Archivo, IBM Plex Mono) ne servent qu’aux libellés.
- Assortiment des icônes Social et Régie : proposition, à valider.
