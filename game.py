import pygame
from typing import List

class Game():
    def __init__(self,screen):
        self.screen = screen
        self._init_text()

    def _init_text(self):
        self.header_font = pygame.font.SysFont("ComicSans.tff",32)
        self.points_font = pygame.font.SysFont("ComicSans.tff",64)
        self.progbar_spec = (220,18,200,50)
        
        self.score_header_text = self.header_font.render("Test Points:",True,(255,0,0),None)
        self.score_text = self.points_font.render("0",True,(255,0,0),None)
        self.coverage_header_text = self.header_font.render("Coverage Points:",True,(255,0,0),None)
        self.coverage_text = self.points_font.render("0",True,(255,0,0),None)
        self.bug_description_texts = []
        self.bug_description_rects = []
        self.progress_text = self.header_font.render("0 / 100",True,(0,0,0),None)
        self.level_text = self.header_font.render("LV. 1",True,(0,0,0),None)

        self.score_header_rect = self.score_header_text.get_rect()
        self.score_text_rect = self.score_text.get_rect()
        self.coverage_header_rect = self.coverage_header_text.get_rect()
        self.coverage_text_rect = self.coverage_text.get_rect()
        self.progress_text_rect = self.progress_text.get_rect()
        self.level_text_rect = self.level_text.get_rect()
        
        self.score_header_rect.center = (128,86)
        self.score_text_rect.center = (128,240)
        self.coverage_header_rect.center = (384,86)
        self.coverage_text_rect.center = (384,240)
        self.progress_text_rect.center = (self.progbar_spec[0] + self.progbar_spec[2]/2,self.progbar_spec[1] + self.progbar_spec[3]/2)
        self.level_text_rect.center = (self.progbar_spec[0]-60,43)
        
        self.progress_bar = pygame.rect.Rect(self.progbar_spec[0],self.progbar_spec[1],50,self.progbar_spec[3])

    def update_global_coverage_progress(self,cases_covered: int,max_cases: int):
        level = 1
        last_target = 0
        target = 50
        while cases_covered >= target:
            last_target = target
            target = int(target * 1.5)
            level += 1
        
        if target >= max_cases:
            target = max_cases

        self.progress_text = self.header_font.render(str(cases_covered)+" / "+str(target),True,(0,0,0),None)
        bar_width = ((cases_covered - last_target)/(target - last_target)) * self.progbar_spec[2]
        self.progress_bar = pygame.rect.Rect(self.progbar_spec[0],self.progbar_spec[1],bar_width,self.progbar_spec[3])
        self.level_text = self.header_font.render("LV. "+str(level)+"/31",True,(0,0,0),None)
    
    def update_score_text(self,test_points: str,coverage_points: str,bug_descriptions: List[str]):
        self.score_text = self.points_font.render(test_points,True,(255,0,0),None)
        self.coverage_text = self.points_font.render(coverage_points,True,(255,0,0),None)
        for desc in bug_descriptions:
            txt = self.header_font.render(desc,True,(255,0,0),None)
            self.bug_description_texts.append(txt)
            self.bug_description_rects.append(txt.get_rect())

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
    
    def render(self):
        self.screen.fill((255,255,255))
        self.screen.blit(self.score_header_text,self.score_header_rect)
        self.screen.blit(self.coverage_header_text,self.coverage_header_rect)
        self.screen.blit(self.score_text,self.score_text_rect)
        self.screen.blit(self.coverage_text,self.coverage_text_rect)
        self.screen.blit(self.level_text,self.level_text_rect)
        glob_prog_text = self.header_font.render("Total Coverage Progress:",True,(0,0,0),None)
        glob_prog_rect = glob_prog_text.get_rect()
        glob_prog_rect.center = (320,10)
        self.screen.blit(glob_prog_text,glob_prog_rect)

        size = len(self.bug_description_texts)
        for i in range(size):
            index = size - i - 1
            self.bug_description_rects[index].center = (320,320 + i * 18)
            self.screen.blit(self.bug_description_texts[index],self.bug_description_rects[index])

        pygame.draw.rect(self.screen,(150,150,150),pygame.rect.Rect(self.progbar_spec[0],self.progbar_spec[1],self.progbar_spec[2],self.progbar_spec[3]))
        pygame.draw.rect(self.screen,(0,0,200),self.progress_bar)
        self.screen.blit(self.progress_text,self.progress_text_rect)
        pygame.display.update()